"""Review analysis service — orchestrates PR fetching, caching, analysis, and persistence."""

import asyncio
import logging
import time

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.interfaces import GitHubProvider
from app.agents.review.orchestrator import ReviewOrchestrator, should_use_multi_agent
from app.core.config import Settings
from app.core.db import async_session
from app.schemas.review import ReviewAnalyzeResponse
from app.services.llm import LLMReviewService
from app.services.review import progress as pg
from app.services.review import (
    create_pending_record,
    find_cached_record,
    save_completed_record,
    save_failed_record,
    set_record_running,
)

logger = logging.getLogger(__name__)


class ReviewAnalysisService:
    """Orchestrates a full PR review analysis from fetch to persistence."""

    def __init__(
        self,
        github_service: GitHubProvider,
        settings: Settings,
    ) -> None:
        self.github_service = github_service
        self.settings = settings

    async def analyze(
        self,
        pr_url: str,
        user_id: int,
        db: AsyncSession,
        redis,
    ) -> ReviewAnalyzeResponse | JSONResponse:
        pr_data = await self.github_service.fetch_pr(pr_url)
        pr_sha = pr_data.head_sha

        # ── cache check ──
        if pr_sha:
            cached = await find_cached_record(db, user_id, pr_sha, redis=redis)
            if cached is not None:
                logger.info("命中缓存 | pr_sha=%s", pr_sha[:12])
                return cached

        # ── pending record ──
        record_id = await create_pending_record(
            db, user_id, pr_url,
            pr_data.title, pr_data.owner, pr_data.repo, pr_data.number, pr_sha,
        )

        # ── route to multi / single agent ──
        if should_use_multi_agent(pr_data):
            return await self._run_multi_agent(pr_url, pr_data, record_id, redis)

        return await self._run_single_agent(pr_url, pr_data, record_id, db, redis)

    # ── multi-agent (background task) ──────────────────────────

    async def _run_multi_agent(
        self,
        pr_url: str,
        pr_data,
        record_id: int,
        redis,
    ) -> JSONResponse:
        github_service = self.github_service

        async def _run_analysis():
            try:
                async with async_session() as task_db:
                    await set_record_running(task_db, record_id)

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

        asyncio.create_task(_run_analysis())
        return JSONResponse(status_code=202, content={"record_id": record_id, "status": "running"})

    # ── single-agent (inline) ──────────────────────────────────

    async def _run_single_agent(
        self,
        pr_url: str,
        pr_data,
        record_id: int,
        db: AsyncSession,
        redis,
    ) -> ReviewAnalyzeResponse:
        started_at = time.perf_counter()
        try:
            orchestrator = ReviewOrchestrator(self.github_service)
            response = await orchestrator.analyze(pr_url, pr_data)
            response.analysis_mode = "single"
        except Exception:
            await save_failed_record(db, record_id)
            raise

        await save_completed_record(db, record_id, response, analysis_mode="single", redis=redis)
        logger.info("持久化完成 | record_id=%d", record_id)
        return response
