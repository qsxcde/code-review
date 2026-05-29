import time
from typing import Any

from app.schemas.github import GitHubPR, GitHubPRFile
from app.schemas.review import (
    ReviewAnalyzeResponse,
    ReviewMetrics,
    ReviewPRInfo,
    ReviewResult,
)

SKIPPED_FILE_SUFFIXES = (
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
)
SKIPPED_FILE_PARTS = (
    "/dist/",
    "/build/",
    "/node_modules/",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
)
MAX_FILES_FOR_CONTEXT = 30
MAX_PATCH_CHARS = 6000


def should_skip_file(filename: str) -> bool:
    normalized_filename = filename.replace("\\", "/")
    normalized = f"/{normalized_filename}"
    return normalized.endswith(SKIPPED_FILE_SUFFIXES) or any(
        part in normalized for part in SKIPPED_FILE_PARTS
    )


def select_files_for_context(files: list[GitHubPRFile]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for file in files:
        if len(selected) >= MAX_FILES_FOR_CONTEXT:
            break
        if should_skip_file(file.filename) or not file.patch:
            continue

        patch = file.patch
        truncated = len(patch) > MAX_PATCH_CHARS
        selected.append(
            {
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "changes": file.changes,
                "patch": patch[:MAX_PATCH_CHARS],
                "truncated": truncated,
            }
        )

    return selected


def has_truncated_patch(files: list[GitHubPRFile]) -> bool:
    return any(file.patch and len(file.patch) > MAX_PATCH_CHARS for file in files)


def build_context(pr_data: GitHubPR) -> tuple[dict[str, Any], int]:
    files = select_files_for_context(pr_data.files)
    context: dict[str, Any] = {
        "prUrl": pr_data.html_url,
        "title": pr_data.title,
        "description": pr_data.body,
        "author": pr_data.author,
        "baseBranch": pr_data.base_branch,
        "headBranch": pr_data.head_branch,
        "changedFiles": pr_data.changed_files,
        "additions": pr_data.additions,
        "deletions": pr_data.deletions,
        "files": files,
        "contextNotes": [
            "过大的 patch 已被截断。" if has_truncated_patch(pr_data.files) else "",
            "lock 文件、构建产物和二进制资源默认不送入模型。",
        ],
    }
    context["contextNotes"] = [note for note in context["contextNotes"] if note]
    return context, len(files)


def normalize_analysis(
    analysis: ReviewResult,
    analyzed_file_count: int,
) -> ReviewResult:
    warnings = list(analysis.warnings)
    risks: list[Any] = []
    low_confidence_filtered_count = 0
    missing_file_high_risk_count = 0

    for risk in analysis.risks:
        if risk.confidence < 0.5:
            low_confidence_filtered_count += 1
            continue

        if risk.severity == "high" and not risk.file:
            missing_file_high_risk_count += 1
            risks.append(risk.model_copy(update={"file": "unknown"}))
            continue

        risks.append(risk)

    if low_confidence_filtered_count:
        warnings.append(
            f"已过滤 {low_confidence_filtered_count} 个置信度低于 50% 的风险项。"
        )
    if missing_file_high_risk_count:
        warnings.append(
            f"已保留 {missing_file_high_risk_count} 个缺少文件定位的高风险项，并将文件标记为 unknown。"
        )

    suggestions_by_key: dict[tuple[str, str, str], Any] = {}
    for suggestion in analysis.suggestions:
        key = (suggestion.file, suggestion.type, suggestion.comment)
        suggestions_by_key[key] = suggestion

    metrics = ReviewMetrics(
        highRiskCount=sum(1 for risk in risks if risk.severity == "high"),
        mediumRiskCount=sum(1 for risk in risks if risk.severity == "medium"),
        lowRiskCount=sum(1 for risk in risks if risk.severity == "low"),
        analyzedFileCount=analyzed_file_count,
    )

    return ReviewResult(
        summary=analysis.summary,
        risks=risks,
        suggestions=list(suggestions_by_key.values()),
        metrics=metrics,
        warnings=warnings,
    )


def build_validate_response(
    pr_data: GitHubPR,
    analysis: ReviewResult,
    started_at: float,
) -> ReviewAnalyzeResponse:
    response = ReviewAnalyzeResponse(
        pr=ReviewPRInfo(
            title=pr_data.title,
            url=pr_data.html_url,
            author=pr_data.author,
            owner=pr_data.owner,
            repo=pr_data.repo,
            number=pr_data.number,
            baseBranch=pr_data.base_branch,
            headBranch=pr_data.head_branch,
        ),
        analysis=analysis,
        durationMs=int((time.perf_counter() - started_at) * 1000),
    )
    return response
