import time
from typing import Any

from app.agents.state import ReviewState
from app.schemas.github import GitHubPR, GitHubPRFile
from app.schemas.review import (
    ReviewAnalyzeResponse,
    ReviewMetrics,
    ReviewPRInfo,
    ReviewResult,
)
from app.services.github_pr import GitHubPRService
from app.services.llm_review import LLMReviewService

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


class ReviewWorkflowNodes:
    def __init__(
        self,
        github_service: GitHubPRService,
        llm_service: LLMReviewService,
    ) -> None:
        self.github_service = github_service
        self.llm_service = llm_service

    async def parse_pr_url(self, state: ReviewState) -> ReviewState:
        owner, repo, pull_number = self.github_service.parse_pr_url(state["pr_url"])
        return {
            **state,
            "owner": owner,
            "repo": repo,
            "pull_number": pull_number,
        }

    async def fetch_pr_data(self, state: ReviewState) -> ReviewState:
        pr_data = await self.github_service.fetch_parsed_pr(
            state["owner"],
            state["repo"],
            state["pull_number"],
        )
        return {
            **state,
            "pr_data": pr_data,
        }

    async def build_context(self, state: ReviewState) -> ReviewState:
        pr_data = state["pr_data"]
        files = self._select_files_for_context(pr_data.files)
        context = {
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
                "过大的 patch 已被截断。" if self._has_truncated_patch(pr_data.files) else "",
                "lock 文件、构建产物和二进制资源默认不送入模型。",
            ],
        }
        context["contextNotes"] = [note for note in context["contextNotes"] if note]

        return {
            **state,
            "context": context,
        }

    async def analyze_review(self, state: ReviewState) -> ReviewState:
        analysis = await self.llm_service.analyze_payload(state["context"])
        return {
            **state,
            "analysis": analysis,
        }

    async def validate_result(self, state: ReviewState) -> ReviewState:
        analysis = self._normalize_analysis(state["analysis"])
        pr_data = state["pr_data"]
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
            durationMs=int((time.perf_counter() - state["started_at"]) * 1000),
        )
        return {
            **state,
            "analysis": analysis,
            "response": response,
        }

    def _select_files_for_context(self, files: list[GitHubPRFile]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []

        for file in files:
            if len(selected) >= MAX_FILES_FOR_CONTEXT:
                break
            if self._should_skip_file(file.filename) or not file.patch:
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

    def _should_skip_file(self, filename: str) -> bool:
        normalized_filename = filename.replace("\\", "/")
        normalized = f"/{normalized_filename}"
        return normalized.endswith(SKIPPED_FILE_SUFFIXES) or any(
            part in normalized for part in SKIPPED_FILE_PARTS
        )

    def _has_truncated_patch(self, files: list[GitHubPRFile]) -> bool:
        return any(file.patch and len(file.patch) > MAX_PATCH_CHARS for file in files)

    def _normalize_analysis(self, analysis: ReviewResult) -> ReviewResult:
        risks = [
            risk
            for risk in analysis.risks
            if risk.confidence >= 0.5 and not (risk.severity == "high" and not risk.file)
        ]
        suggestions_by_key = {}
        for suggestion in analysis.suggestions:
            key = (suggestion.file, suggestion.type, suggestion.comment)
            suggestions_by_key[key] = suggestion

        metrics = ReviewMetrics(
            highRiskCount=sum(1 for risk in risks if risk.severity == "high"),
            mediumRiskCount=sum(1 for risk in risks if risk.severity == "medium"),
            lowRiskCount=sum(1 for risk in risks if risk.severity == "low"),
            analyzedFileCount=analysis.metrics.analyzedFileCount,
        )

        return ReviewResult(
            summary=analysis.summary,
            risks=risks,
            suggestions=list(suggestions_by_key.values()),
            metrics=metrics,
        )
