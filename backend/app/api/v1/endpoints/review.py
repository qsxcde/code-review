import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.review.orchestrator import ReviewOrchestrator
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.rate_limit import require_rate_limit
from app.core.security import require_jwt_user
from app.schemas.review import (
    MockReviewRequest,
    ReviewAnalyzeRequest,
    ReviewAnalyzeResponse,
    ReviewResult,
)
from app.services.github import get_github_pr_service
from app.services.llm import LLMReviewService
from app.services.review.history import (
    create_pending_record,
    find_cached_record,
    save_completed_record,
    save_failed_record,
)

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
        cached = await find_cached_record(db, user_id, pr_sha)
        if cached is not None:
            return cached

    record_id = await create_pending_record(
        db, user_id, pr_url,
        pr_data.title, pr_data.owner, pr_data.repo, pr_data.number, pr_sha,
    )

    started_at = time.perf_counter()
    try:
        orchestrator = ReviewOrchestrator(github_service)
        response = await orchestrator.analyze(pr_url, pr_data)
    except Exception:
        await save_failed_record(db, record_id)
        raise

    await save_completed_record(db, record_id, response)
    return response
