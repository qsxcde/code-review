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
from app.schemas.review import (
    ReviewAnalyzeResponse,
    ReviewMetrics,
    ReviewResult,
    RiskTrend,
)
from app.services.review.progress import publish_complete, publish_error, publish_progress
from app.services.review.record_service import (
    create_pending_record,
    find_cached_record,
    find_previous_record,
    save_completed_record,
    save_failed_record,
    set_record_running,
)
from app.services.review.rule_service import get_enabled_rules

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

        # ── fetch PR discussion (non-blocking, graceful degradation) ──
        discussion = await self._safe_fetch_discussion(pr_data)

        # ── load custom review rules ──
        custom_rules = await self._safe_fetch_rules(db, user_id)

        # ── cache check (exact SHA match → full response cached) ──
        if pr_sha:
            cached = await find_cached_record(db, user_id, pr_sha, redis=redis)
            if cached is not None:
                logger.info("命中缓存 | pr_sha=%s", pr_sha[:12])
                return cached

        # ── incremental check: compare with previous analysis ──
        incremental_files = None
        previous_response = None
        previous = await find_previous_record(
            db, user_id, pr_data.owner, pr_data.repo, pr_data.number,
        )
        if previous and previous.pr_sha and previous.pr_sha != pr_sha:
            incremental_files = await self.github_service.fetch_compare(
                pr_data.owner, pr_data.repo, previous.pr_sha, pr_sha,
            )
            if incremental_files and previous.result_json:
                try:
                    previous_response = ReviewAnalyzeResponse.model_validate(
                        previous.result_json
                    )
                except Exception:
                    logger.debug("Previous result JSON parse failed", exc_info=True)

        # ── pending record ──
        record_id = await create_pending_record(
            db, user_id, pr_url,
            pr_data.title, pr_data.owner, pr_data.repo, pr_data.number, pr_sha,
        )

        # ── route ──
        if should_use_multi_agent(pr_data):
            return await self._run_multi_agent(pr_url, pr_data, record_id, redis, discussion, custom_rules)

        response = await self._run_single_agent(pr_url, pr_data, record_id, db, redis, discussion, custom_rules)

        # ── merge incremental result ──
        if incremental_files and previous_response:
            response = self._merge_incremental(response, previous_response, incremental_files)

        return response

    # ── helpers ────────────────────────────────────────────────

    def _merge_incremental(
        self,
        new_response: ReviewAnalyzeResponse,
        previous: ReviewAnalyzeResponse,
        changed_files: list[dict[str, object]],
    ) -> ReviewAnalyzeResponse:
        """Merge new analysis with previous: keep old risks for unchanged files."""
        changed_filenames = {f["filename"] for f in changed_files}

        # risks from previous analysis that are for UNCHANGED files
        old_unchanged_risks = [
            r for r in previous.analysis.risks
            if r.file not in changed_filenames
        ]
        # risks from previous that are for CHANGED files (now "fixed" or gone)
        old_changed_risks = [
            r for r in previous.analysis.risks
            if r.file in changed_filenames
        ]

        # new risks (from current analysis)
        new_risks = new_response.analysis.risks

        all_risks = old_unchanged_risks + new_risks

        # build trend
        trend = RiskTrend(
            new=len(new_risks),
            fixed=len(old_changed_risks),
            unchanged=len(old_unchanged_risks),
        )

        # recalc metrics
        metrics = ReviewMetrics(
            highRiskCount=sum(1 for r in all_risks if r.severity == "high"),
            mediumRiskCount=sum(1 for r in all_risks if r.severity == "medium"),
            lowRiskCount=sum(1 for r in all_risks if r.severity == "low"),
            analyzedFileCount=new_response.analysis.metrics.analyzedFileCount,
        )

        merged_result = ReviewResult(
            summary=new_response.analysis.summary,
            risks=all_risks,
            suggestions=new_response.analysis.suggestions,
            metrics=metrics,
            warnings=new_response.analysis.warnings,
        )

        response = ReviewAnalyzeResponse(
            pr=new_response.pr,
            analysis=merged_result,
            durationMs=new_response.durationMs,
            analysis_mode=new_response.analysis_mode,
            analysis_type="incremental",
            risk_trend=trend,
        )
        return response

    async def _safe_fetch_rules(self, db, user_id):
        """Load enabled custom rules with graceful degradation."""
        try:
            return await get_enabled_rules(db, user_id)
        except Exception:
            logger.debug("自定义规则加载失败", exc_info=True)
            return []

    async def _safe_fetch_discussion(self, pr_data):
        """Fetch discussion with graceful degradation."""
        try:
            return await self.github_service.fetch_discussion(
                pr_data.owner, pr_data.repo, pr_data.number,
            )
        except Exception:
            logger.debug("PR 讨论获取失败，继续无讨论上下文分析", exc_info=True)
            return None

    # ── multi-agent (background task) ──────────────────────────

    async def _run_multi_agent(
        self,
        pr_url: str,
        pr_data,
        record_id: int,
        redis,
        discussion=None,
        custom_rules=None,
    ) -> JSONResponse:
        github_service = self.github_service

        async def _run_analysis():
            try:
                async with async_session() as task_db:
                    await set_record_running(task_db, record_id)

                    async def _on_progress(event: str, **kwargs):
                        await publish_progress(redis, record_id, event, **kwargs)

                    orchestrator = ReviewOrchestrator(github_service)
                    response = await orchestrator.analyze(
                        pr_url, pr_data, on_progress=_on_progress,
                        discussion=discussion, custom_rules=custom_rules,
                    )
                    response.analysis_mode = "multi"
                    await save_completed_record(task_db, record_id, response, analysis_mode="multi", redis=redis)
                    await publish_complete(redis, record_id)
            except Exception as exc:
                async with async_session() as task_db:
                    await save_failed_record(task_db, record_id)
                await publish_error(redis, record_id, "orchestrator", str(exc)[:200], 0)

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
        discussion=None,
        custom_rules=None,
    ) -> ReviewAnalyzeResponse:
        started_at = time.perf_counter()
        try:
            orchestrator = ReviewOrchestrator(self.github_service)
            response = await orchestrator.analyze(
                pr_url, pr_data, discussion=discussion, custom_rules=custom_rules,
            )
            response.analysis_mode = "single"
        except Exception:
            await save_failed_record(db, record_id)
            raise

        await save_completed_record(db, record_id, response, analysis_mode="single", redis=redis)
        logger.info("持久化完成 | record_id=%d", record_id)
        return response
