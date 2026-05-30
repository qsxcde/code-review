"""Review orchestrator: complexity routing + multi-agent orchestration."""
import asyncio
import json
import logging
import time

from app.agents.review.aggregator import detect_conflicts, merge_results
from app.agents.review.graph import ReviewGraphRunner
from app.agents.review.specialist import MULTI_AGENTS, SpecialistAgent
from app.core.config import settings
from app.schemas.github import GitHubPR
from app.schemas.review import ReviewAnalyzeResponse, ReviewPRInfo, ReviewResult
from app.services.github import GitHubPRService
from app.services.llm.service import LLMReviewService

logger = logging.getLogger(__name__)

SINGLE_MAX_FILES = 3
SINGLE_MAX_LINES = 1000
MULTI_MIN_FILES = 10
MULTI_MIN_LINES = 5000


def _should_use_multi_agent(pr_data: GitHubPR) -> bool:
    total_lines = pr_data.additions + pr_data.deletions
    files = pr_data.changed_files

    if files <= SINGLE_MAX_FILES and total_lines <= SINGLE_MAX_LINES:
        return False
    if files > MULTI_MIN_FILES or total_lines > MULTI_MIN_LINES:
        return True
    return False


async def _run_single_agent(
    github_service: GitHubPRService,
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
    result = await llm.analyze_payload(context, system_prompt=agent.system_prompt)
    return agent.category_prefix, result


async def _phase1_analyze_pr(pr_data: GitHubPR) -> dict | None:
    from app.agents.review.prompts.orchestrator_phase1 import SYSTEM_PROMPT

    try:
        languages = list({f.filename.split(".")[-1] for f in pr_data.files if "." in f.filename})
        file_list = [f.filename for f in pr_data.files[:20]]
        phase1_payload = {
            "pr_title": pr_data.title,
            "changed_files": pr_data.changed_files,
            "additions": pr_data.additions,
            "deletions": pr_data.deletions,
            "languages": languages,
            "file_list": file_list,
        }
        llm = LLMReviewService(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.deep_model,
        )
        wrapper = {"pr_payload": json.dumps(phase1_payload, ensure_ascii=False)}
        result = await llm.analyze_payload(wrapper, system_prompt=SYSTEM_PROMPT)
        return json.loads(result.summary.overview)
    except Exception:
        logger.warning("Phase 1 failed, proceeding without focus notes", exc_info=True)
        return None


async def _phase2_summarize(
    merged_response: ReviewAnalyzeResponse,
    conflicts: list[dict],
) -> ReviewAnalyzeResponse:
    from app.agents.review.prompts.orchestrator_phase2 import SYSTEM_PROMPT

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
        wrapper = {"pr_payload": json.dumps(summary_data, ensure_ascii=False)}
        result = await llm.analyze_payload(wrapper, system_prompt=SYSTEM_PROMPT)
        phase2_data = json.loads(result.summary.overview)
        merged_response.analysis.summary.overview = phase2_data.get("overview", "")
        merged_response.analysis.summary.impact = phase2_data.get("impact", [])
    except Exception:
        logger.warning("Phase 2 failed, using merged summary", exc_info=True)

    return merged_response


async def _run_multi_agent(
    github_service: GitHubPRService,
    pr_data: GitHubPR,
    context_builder,
    pr_url: str,
) -> ReviewAnalyzeResponse:
    started_at = time.perf_counter()

    # Phase 1: PR feature analysis (runs in parallel with context building externally)
    focus_notes_task = _phase1_analyze_pr(pr_data)

    # Build per-agent contexts
    contexts = context_builder.build_filtered(pr_data, MULTI_AGENTS)

    # Wait for Phase 1
    focus_notes = await focus_notes_task

    # Run 3 agents in parallel
    tasks = []
    for agent in MULTI_AGENTS:
        ctx = contexts.get(agent.name, {"files": [], "file_count": 0})
        tasks.append(_run_single_agent_for(agent, ctx))

    agent_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect valid results
    valid_results: list[tuple[str, ReviewResult]] = []
    for agent, result in zip(MULTI_AGENTS, agent_results):
        if isinstance(result, Exception):
            logger.error("Agent %s failed: %s", agent.name, result)
            continue
        valid_results.append(result)

    if not valid_results:
        raise RuntimeError("All specialist agents failed")

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
    merged = merge_results(valid_results, pr_info, duration_ms)
    conflicts = detect_conflicts(merged.analysis.risks)
    merged = await _phase2_summarize(merged, conflicts)

    return merged


class ReviewOrchestrator:
    def __init__(self, github_service: GitHubPRService):
        self.github_service = github_service

    async def analyze(self, pr_url: str, pr_data: GitHubPR) -> ReviewAnalyzeResponse:
        if _should_use_multi_agent(pr_data):
            logger.info(
                "Using multi-agent analysis for PR (files=%d, lines=%d)",
                pr_data.changed_files,
                pr_data.additions + pr_data.deletions,
            )
            from app.agents.review.context import ReviewContextBuilder

            context_builder = ReviewContextBuilder()
            return await _run_multi_agent(
                self.github_service, pr_data, context_builder, pr_url
            )

        logger.info(
            "Using single-agent analysis for PR (files=%d, lines=%d)",
            pr_data.changed_files,
            pr_data.additions + pr_data.deletions,
        )
        return await _run_single_agent(self.github_service, pr_url)
