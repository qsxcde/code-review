"""Merge results from multiple specialist agents into one ReviewResult."""
import logging

from app.schemas.review import (
    ReviewAnalyzeResponse,
    ReviewMetrics,
    ReviewPRInfo,
    ReviewResult,
    RiskItem,
    ReviewSuggestion,
    ReviewSummary,
)

logger = logging.getLogger(__name__)


def merge_results(
    results: list[tuple[str, ReviewResult]],
    pr_info: ReviewPRInfo,
    duration_ms: int,
) -> ReviewAnalyzeResponse:
    risks: list[RiskItem] = []
    suggestions: list[ReviewSuggestion] = []
    warnings: list[str] = []
    overview_parts: list[str] = []
    changed_modules: list[str] = []

    for category, result in results:
        overview_parts.append(f"[{category}] {result.summary.overview}")
        changed_modules.extend(result.summary.changedModules)
        for risk in result.risks:
            risk.issue = f"{category} {risk.issue}"
            risks.append(risk)
        for sug in result.suggestions:
            sug.comment = f"{category} {sug.comment}"
            suggestions.append(sug)
        warnings.extend(result.warnings)

    risks = _deduplicate_risks(risks)
    unique_modules = list(dict.fromkeys(changed_modules))

    summary = ReviewSummary(
        overview=" ".join(overview_parts),
        changedModules=unique_modules,
        impact=[],
    )

    metrics = ReviewMetrics(
        highRiskCount=sum(1 for r in risks if r.severity == "high"),
        mediumRiskCount=sum(1 for r in risks if r.severity == "medium"),
        lowRiskCount=sum(1 for r in risks if r.severity == "low"),
        analyzedFileCount=pr_info.changedFiles,
    )

    merged_result = ReviewResult(
        summary=summary,
        risks=risks,
        suggestions=suggestions,
        metrics=metrics,
        warnings=warnings,
    )

    return ReviewAnalyzeResponse(
        pr=pr_info,
        analysis=merged_result,
        durationMs=duration_ms,
    )


def detect_conflicts(risks: list[RiskItem]) -> list[dict]:
    """Detect risks at same file+line from different agents with severity conflicts."""
    conflicts: list[dict] = []
    seen: dict[tuple[str, int], list[RiskItem]] = {}
    for risk in risks:
        key = (risk.file, risk.line or 0)
        if key not in seen:
            seen[key] = []
        seen[key].append(risk)
    for key, items in seen.items():
        if len(items) >= 2:
            severities = {r.severity for r in items}
            if len(severities) > 1:
                conflicts.append({
                    "file": key[0],
                    "line": key[1],
                    "issue": f"Severity conflict: {severities}",
                    "agent_issues": [r.issue for r in items],
                })
    return conflicts


def _deduplicate_risks(
    risks: list[RiskItem],
) -> list[RiskItem]:
    """Dedup by file + line + category prefix. Higher priority agents win."""
    seen: dict[tuple[str, int, str], RiskItem] = {}
    priority: dict[str, int] = {"[安全]": 0, "[性能]": 1, "[风格]": 2}

    for risk in risks:
        prefix = "[安全]"
        for tag in priority:
            if risk.issue.startswith(tag):
                prefix = tag
                break
        key = (risk.file, risk.line or 0, prefix)
        if key not in seen:
            seen[key] = risk
        else:
            existing_prefix = "[安全]"
            for tag in priority:
                if seen[key].issue.startswith(tag):
                    existing_prefix = tag
                    break
            if priority.get(prefix, 9) < priority.get(existing_prefix, 9):
                seen[key] = risk
    return list(seen.values())
