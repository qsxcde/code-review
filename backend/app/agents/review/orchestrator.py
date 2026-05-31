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
from app.schemas.github import GitHubPR, PRDiscussion
from app.schemas.review import ReviewAnalyzeResponse, ReviewPRInfo, ReviewResult
from app.services.llm.service import LLMReviewService

logger = logging.getLogger(__name__)

SINGLE_MAX_FILES = 2
SINGLE_MAX_LINES = 300
MULTI_MIN_FILES = 4
MULTI_MIN_LINES = 1000

# ── discussion formatting ──────────────────────────────────────
DISCUSSION_MAX_CHARS = 2000
DISCUSSION_MAX_COMMENTS = 15
DISCUSSION_COMMENT_CHARS = 200
DISCUSSION_SUMMARIZE_THRESHOLD = 30  # Phase 2: switch to LLM summary when >30 comments


def _format_discussion(discussion: PRDiscussion | None) -> str:
    """Convert PRDiscussion to a compact text string for prompt injection.

    Priority: PR author's comments > maintainer comments > others.
    Total output capped at DISCUSSION_MAX_CHARS.
    """
    if discussion is None:
        return ""

    parts: list[str] = []

    if discussion.pr_body:
        parts.append(f"[PR 描述] {discussion.pr_body[:800]}")

    all_comments = discussion.issue_comments + discussion.review_comments
    if not all_comments:
        return "\n".join(parts)

    # sort: PR author first, then by recency
    pr_author = ""
    if discussion.issue_comments:
        pr_author = ""  # we infer author from discussion context — keep simple

    sorted_comments = sorted(
        all_comments,
        key=lambda c: c.created_at,
        reverse=True,
    )[:DISCUSSION_MAX_COMMENTS]

    for c in sorted_comments:
        author_tag = f"[{c.author}]"
        body = c.body[:DISCUSSION_COMMENT_CHARS].replace("\n", " ")
        parts.append(f"{author_tag} {body}")

    result = "\n".join(parts)
    if len(result) > DISCUSSION_MAX_CHARS:
        result = result[:DISCUSSION_MAX_CHARS] + "\n... (discussion truncated)"
    return result


async def _summarize_discussion(discussion: PRDiscussion) -> str:
    """Phase 2: Use fast_model to summarize lengthy discussion threads.

    Falls back to _format_discussion on any error.
    """
    all_comments = discussion.issue_comments + discussion.review_comments
    total = len(all_comments)

    # Build raw discussion text for the LLM
    lines: list[str] = []
    if discussion.pr_body:
        lines.append(f"[PR 描述] {discussion.pr_body[:1000]}")
    for c in sorted(all_comments, key=lambda x: x.created_at, reverse=True):
        lines.append(f"[{c.author}] {c.body[:300].replace(chr(10), ' ')}")

    raw = "\n".join(lines)

    summary_prompt = (
        "你是一个代码评审助手。请从以下 PR 讨论记录中提取与代码审查相关的关键信息。"
        "重点关注：作者的设计意图、已知限制、安全性讨论、性能关注点、以及任何关于代码变更的争议或共识。"
        "只返回严格 JSON，不要 Markdown 或额外解释。"
    )
    summary_payload = {
        "total_comments": total,
        "discussion": raw[:5000],
    }

    try:
        llm = LLMReviewService(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.fast_model,
        )
        result = await llm.analyze_json_payload(
            summary_payload,
            system_prompt=summary_prompt,
            stage="discussion_summary",
        )
        summary = result.get("summary", "")
        key_points = result.get("key_points", [])
        if key_points:
            summary += "\n关键讨论点：\n" + "\n".join(f"- {p}" for p in key_points)
        return summary[:DISCUSSION_MAX_CHARS]
    except Exception:
        logger.warning("讨论摘要失败，回退到简单格式化", exc_info=True)
        return _format_discussion(discussion)


def should_use_multi_agent(pr_data: GitHubPR) -> bool:
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


async def _phase1_analyze_pr(
    pr_data: GitHubPR, discussion: PRDiscussion | None = None
) -> dict | None:
    try:
        # Phase 2: summarize discussion when comments exceed threshold
        discussion_context = ""
        discussion_task = None
        if discussion:
            total_comments = len(discussion.issue_comments) + len(discussion.review_comments)
            if total_comments > DISCUSSION_SUMMARIZE_THRESHOLD:
                discussion_task = asyncio.create_task(
                    _summarize_discussion(discussion)
                )
            else:
                discussion_context = _format_discussion(discussion)

        languages = list({f.filename.split(".")[-1] for f in pr_data.files if "." in f.filename})
        lang_rules = build_language_rules(languages)
        file_list = [f.filename for f in pr_data.files[:20]]

        # await discussion summary if it was started
        if discussion_task:
            discussion_context = await discussion_task

        phase1_payload = {
            "pr_title": pr_data.title,
            "changed_files": pr_data.changed_files,
            "additions": pr_data.additions,
            "deletions": pr_data.deletions,
            "languages": languages,
            "file_list": file_list,
            "language_rules": lang_rules,
            "pr_description": pr_data.body or "",
            "discussion_context": discussion_context,
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
    discussion: PRDiscussion | None = None,
) -> ReviewAnalyzeResponse:
    started_at = time.perf_counter()

    # Phase 1: PR feature analysis (runs in parallel with context building externally)
    focus_notes_task = _phase1_analyze_pr(pr_data, discussion)

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
                "跳过Agent：PR 未涉及该领域代码变更",
                extra={"props": {"agent": agent.name, "stage": f"agent:{agent.name}"}},
            )
            if on_progress:
                await on_progress(
                    "agent_skipped",
                    agent=agent.category_prefix,
                    message="该 PR 未涉及相关领域的代码变更，跳过此专家分析",
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
        self,
        pr_url: str,
        pr_data: GitHubPR,
        on_progress: Callable | None = None,
        discussion: PRDiscussion | None = None,
    ) -> ReviewAnalyzeResponse:
        if should_use_multi_agent(pr_data):
            logger.info(
                "使用多Agent分析",
                extra={"props": {"files": pr_data.changed_files, "lines": pr_data.additions + pr_data.deletions}},
            )
            context_builder = ReviewContextBuilder()
            return await _run_multi_agent(
                self.github_service, pr_data, context_builder, pr_url,
                on_progress=on_progress, discussion=discussion,
            )

        logger.info(
            "使用单Agent分析",
            extra={"props": {"files": pr_data.changed_files, "lines": pr_data.additions + pr_data.deletions}},
        )
        return await _run_single_agent(self.github_service, pr_url)
