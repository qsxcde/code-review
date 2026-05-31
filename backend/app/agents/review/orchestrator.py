"""Review orchestrator: complexity routing + multi-agent orchestration."""
import asyncio
import json
import logging
import time
from collections.abc import Callable

from app.agents.interfaces import GitHubProvider
from app.agents.review.aggregator import detect_conflicts, merge_results
from app.agents.review.context import ReviewContextBuilder
from app.agents.review.graph import ReviewGraphRunner
from app.agents.review.prompts.orchestrator_phase1 import SYSTEM_PROMPT as PHASE1_PROMPT
from app.agents.review.prompts.orchestrator_phase2 import SYSTEM_PROMPT as PHASE2_PROMPT
from app.agents.review.prompts.language_rules import build_language_rules
from app.agents.review.specialist import MULTI_AGENTS, SpecialistAgent
from app.core.config import settings
from app.schemas.github import GitHubPR
from app.schemas.review import ReviewAnalyzeResponse, ReviewPRInfo, ReviewResult
from app.services.llm.service import LLMReviewService

logger = logging.getLogger(__name__)

SINGLE_MAX_FILES = 2
SINGLE_MAX_LINES = 300
MULTI_MIN_FILES = 4
MULTI_MIN_LINES = 1000


def _should_use_multi_agent(pr_data: GitHubPR) -> bool:
    total_lines = pr_data.additions + pr_data.deletions
    files = pr_data.changed_files

    if files <= SINGLE_MAX_FILES and total_lines <= SINGLE_MAX_LINES:
        return False
    if files > MULTI_MIN_FILES or total_lines > MULTI_MIN_LINES:
        return True
    return False


async def _run_single_agent(
    github_service: GitHubProvider,
    pr_url: str,
) -> ReviewAnalyzeResponse:
    llm = LLMReviewService(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.fast_model,
    )
    graph = ReviewGraphRunner(github_service, llm)
    return await graph.analyze(pr_url)


async def _run_single_agent_for(
    agent: SpecialistAgent,
    context: dict,
) -> tuple[str, ReviewResult]:
    llm = LLMReviewService(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=agent.model,
    )
    result = await llm.analyze_payload(
        context,
        system_prompt=agent.system_prompt,
        stage=f"agent:{agent.name}",
    )
    return agent.category_prefix, result


async def _phase1_analyze_pr(pr_data: GitHubPR) -> dict | None:
    try:
        languages = list({f.filename.split(".")[-1] for f in pr_data.files if "." in f.filename})
        lang_rules = build_language_rules(languages)
        file_list = [f.filename for f in pr_data.files[:20]]
        phase1_payload = {
            "pr_title": pr_data.title,
            "changed_files": pr_data.changed_files,
            "additions": pr_data.additions,
            "deletions": pr_data.deletions,
            "languages": languages,
            "file_list": file_list,
            "language_rules": lang_rules,
        }
        llm = LLMReviewService(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.deep_model,
        )
        focus_notes = await llm.analyze_json_payload(
            phase1_payload,
            system_prompt=PHASE1_PROMPT,
            stage="phase1",
        )
        logger.info(
            "阶段1完成",
            extra={"props": {
                "安全重点": str(focus_notes.get("security_focus", ""))[:40],
                "性能重点": str(focus_notes.get("performance_focus", ""))[:40],
            }},
        )
        return focus_notes
    except Exception:
        logger.warning("阶段1失败，继续无焦点分析", exc_info=True)
        return {
            "high_risk_areas": [],
            "attention_files": [],
            "security_focus": lang_rules.get("security", ""),
            "performance_focus": lang_rules.get("performance", ""),
            "style_focus": lang_rules.get("style", ""),
            "global_context": "",
        }


async def _phase2_summarize(
    merged_response: ReviewAnalyzeResponse,
    conflicts: list[dict],
) -> ReviewAnalyzeResponse:
    try:
        summary_data = {
            "risks_count": len(merged_response.analysis.risks),
            "suggestions_count": len(merged_response.analysis.suggestions),
            "risks_summary": [
                {
                    "file": r.file,
                    "line": r.line,
                    "severity": r.severity,
                    "issue": r.issue,
                }
                for r in merged_response.analysis.risks[:15]
            ],
            "suggestions_summary": [
                {"file": s.file, "type": s.type, "comment": s.comment}
                for s in merged_response.analysis.suggestions[:10]
            ],
            "conflicts": conflicts if conflicts else [],
        }
        llm = LLMReviewService(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.deep_model,
        )
        phase2_data = await llm.analyze_json_payload(
            summary_data,
            system_prompt=PHASE2_PROMPT,
            stage="phase2",
        )
        merged_response.analysis.summary.overview = str(phase2_data.get("overview", ""))
        impact = phase2_data.get("impact", [])
        merged_response.analysis.summary.impact = impact if isinstance(impact, list) else []
    except Exception:
        logger.warning("阶段2失败，使用合并摘要", exc_info=True)

    return merged_response


async def _run_multi_agent(
    github_service: GitHubProvider,
    pr_data: GitHubPR,
    context_builder,
    pr_url: str,
    on_progress: Callable | None = None,
) -> ReviewAnalyzeResponse:
    started_at = time.perf_counter()

    # Phase 1: PR feature analysis (runs in parallel with context building externally)
    focus_notes_task = _phase1_analyze_pr(pr_data)

    # Build per-agent contexts
    contexts = context_builder.build_filtered(pr_data, MULTI_AGENTS)

    # Wait for Phase 1
    focus_notes = await focus_notes_task
    if focus_notes:
        for ctx in contexts.values():
            ctx["focusNotes"] = focus_notes

    if on_progress:
        await on_progress("phase_done", phase="phase1", percent=10)

    if on_progress:
        await on_progress("phase_start", phase="phase2", message="启动专家分析", percent=10)

    # Run 3 agents in parallel
    tasks = []
    active_agents = []
    for agent in MULTI_AGENTS:
        ctx = contexts.get(agent.name, {"files": [], "file_count": 0})
        if not ctx.get("files"):
            logger.info(
                "跳过无可分析diff的Agent",
                extra={"props": {"agent": agent.name, "stage": f"agent:{agent.name}"}},
            )
            if on_progress:
                await on_progress(
                    "agent_skipped",
                    agent=agent.category_prefix,
                    message="没有可分析的 diff 内容",
            )
            continue
        active_agents.append(agent)
        tasks.append(_run_single_agent_for(agent, ctx))

    agent_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect valid results
    valid_results: list[tuple[str, ReviewResult]] = []
    for agent, result in zip(active_agents, agent_results):
        if isinstance(result, Exception):
            logger.error(
                "Agent失败",
                exc_info=result,
                extra={
                    "props": {
                        "agent": agent.name,
                        "stage": f"agent:{agent.name}",
                        "error_type": type(result).__name__,
                        "error": str(result)[:500],
                    }
                },
            )
            if on_progress:
                await on_progress(
                    "agent_error",
                    agent=agent.category_prefix,
                    message=str(result)[:200],
                )
            continue
        valid_results.append(result)

    if not valid_results:
        errors = [
            {
                "agent": agent.name,
                "error_type": type(result).__name__,
                "message": str(result)[:500],
            }
            for agent, result in zip(active_agents, agent_results)
            if isinstance(result, Exception)
        ]
        raise RuntimeError(f"All specialist agents failed: {json.dumps(errors, ensure_ascii=False)}")

    for _agent, r in valid_results:
        m = r.metrics
        total_risks = m.highRiskCount + m.mediumRiskCount + m.lowRiskCount
        if on_progress:
            await on_progress("agent_done", agent=_agent, risks=total_risks, high=m.highRiskCount)
        logger.info(
            "%sAgent完成",
            _agent,
            extra={"props": {"risks": total_risks, "high": m.highRiskCount, "medium": m.mediumRiskCount}},
        )

    # Build PR info for response
    pr_info = ReviewPRInfo(
        title=pr_data.title,
        url=pr_data.html_url,
        author=pr_data.author,
        owner=pr_data.owner,
        repo=pr_data.repo,
        number=pr_data.number,
        baseBranch=pr_data.base_branch,
        headBranch=pr_data.head_branch,
        changedFiles=pr_data.changed_files,
        additions=pr_data.additions,
        deletions=pr_data.deletions,
    )

    duration_ms = int((time.perf_counter() - started_at) * 1000)

    if on_progress:
        await on_progress("phase_start", phase="phase3", message="合并结果并生成报告", percent=85)

    merged = merge_results(valid_results, pr_info, duration_ms)
    conflicts = detect_conflicts(merged.analysis.risks)
    merged = await _phase2_summarize(merged, conflicts)

    if on_progress:
        await on_progress("phase_done", phase="phase3", percent=100)

    final_m = merged.analysis.metrics
    total_risks = final_m.highRiskCount + final_m.mediumRiskCount + final_m.lowRiskCount
    logger.info(
        "阶段2完成",
        extra={"props": {"总风险": total_risks, "总建议": len(merged.analysis.suggestions)}},
    )

    return merged


class ReviewOrchestrator:
    def __init__(self, github_service: GitHubProvider):
        self.github_service = github_service

    async def analyze(
        self, pr_url: str, pr_data: GitHubPR, on_progress: Callable | None = None
    ) -> ReviewAnalyzeResponse:
        if _should_use_multi_agent(pr_data):
            logger.info(
                "使用多Agent分析",
                extra={"props": {"files": pr_data.changed_files, "lines": pr_data.additions + pr_data.deletions}},
            )
            context_builder = ReviewContextBuilder()
            return await _run_multi_agent(
                self.github_service, pr_data, context_builder, pr_url, on_progress=on_progress
            )

        logger.info(
            "使用单Agent分析",
            extra={"props": {"files": pr_data.changed_files, "lines": pr_data.additions + pr_data.deletions}},
        )
        return await _run_single_agent(self.github_service, pr_url)
