import asyncio
import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.agents.review.orchestrator import ReviewOrchestrator, _should_use_multi_agent
from app.core.config import Settings, get_settings
from app.core.config import settings as app_settings
from app.core.db import async_session, get_db
from app.core.redis import get_redis
from app.core.rate_limit import require_rate_limit
from app.core.security import require_jwt_user
from app.models.review_record import ReviewRecord
from app.schemas.review import (
    MockReviewRequest,
    ReviewAnalyzeRequest,
    ReviewAnalyzeResponse,
    ReviewResult,
)
from app.services.github import get_github_pr_service
from app.services.llm import LLMReviewService
from app.services.review import progress as pg
from app.services.review.record_service import (
    create_pending_record,
    find_cached_record,
    save_completed_record,
    save_failed_record,
)

logger = logging.getLogger(__name__)


async def save_running_record(db: AsyncSession, record_id: int) -> None:
    result = await db.execute(select(ReviewRecord).where(ReviewRecord.id == record_id))
    record = result.scalar_one_or_none()
    if record is not None:
        record.status = "running"
        await db.commit()


router = APIRouter(
    prefix="/review",
    tags=["review"],
    dependencies=[Depends(require_jwt_user), Depends(require_rate_limit)],
)


@router.post("/mock-analyze", response_model=ReviewResult)
async def analyze_mock_pr(
    request: MockReviewRequest,
    settings: Settings = Depends(get_settings),
) -> ReviewResult:
    service = LLMReviewService(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )
    return await service.analyze_mock_pr(request)


@router.post("/analyze", response_model=ReviewAnalyzeResponse)
async def analyze_pr(
    request: ReviewAnalyzeRequest,
    settings: Settings = Depends(get_settings),
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ReviewAnalyzeResponse:
    github_service = get_github_pr_service(
        token=settings.github_token,
        proxy=settings.github_api_proxy,
    )
    llm_service = LLMReviewService(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )

    pr_url = str(request.pr_url)
    pr_data = await github_service.fetch_pr(pr_url)
    pr_sha = pr_data.head_sha

    if pr_sha:
        cached = await find_cached_record(db, user_id, pr_sha, redis=redis)
        if cached is not None:
            logger.info("命中缓存 | pr_sha=%s", pr_sha[:12])
            return cached

    record_id = await create_pending_record(
        db, user_id, pr_url,
        pr_data.title, pr_data.owner, pr_data.repo, pr_data.number, pr_sha,
    )

    if _should_use_multi_agent(pr_data):
        redis = await aioredis.from_url(app_settings.redis_url, decode_responses=True)

        async def _run_analysis():
            try:
                async with async_session() as task_db:
                    await save_running_record(task_db, record_id)

                    async def _on_progress(event: str, **kwargs):
                        await pg.publish_progress(redis, record_id, event, **kwargs)

                    orchestrator = ReviewOrchestrator(github_service)
                    response = await orchestrator.analyze(pr_url, pr_data, on_progress=_on_progress)
                    response.analysis_mode = "multi"
                    await save_completed_record(task_db, record_id, response, analysis_mode="multi", redis=redis)
                    await pg.publish_complete(redis, record_id)
            except Exception as exc:
                async with async_session() as task_db:
                    await save_failed_record(task_db, record_id)
                await pg.publish_error(redis, record_id, "orchestrator", str(exc)[:200], 0)
            finally:
                await redis.close()

        asyncio.create_task(_run_analysis())
        return JSONResponse(status_code=202, content={"record_id": record_id, "status": "running"})

    started_at = time.perf_counter()
    try:
        orchestrator = ReviewOrchestrator(github_service)
        response = await orchestrator.analyze(pr_url, pr_data)
        response.analysis_mode = "single"
    except Exception:
        await save_failed_record(db, record_id)
        raise

    await save_completed_record(db, record_id, response, analysis_mode="single", redis=redis)
    logger.info("持久化完成 | record_id=%d", record_id)
    return response
