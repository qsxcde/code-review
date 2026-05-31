import logging

import httpx
from fastapi import HTTPException, status

from app.schemas.github import GitHubPR, PRComment, PRDiscussion
from app.services.github.client import GITHUB_NETWORK_ERROR_MESSAGES, GitHubAPIClient
from app.services.github.mapper import map_github_pr_response
from app.services.github.parser import parse_pr_url

logger = logging.getLogger(__name__)


class GitHubPRService:
    def __init__(
        self,
        token: str | None = None,
        proxy: str | None = None,
    ) -> None:
        self.client = GitHubAPIClient(token=token, proxy=proxy)

    async def aclose(self) -> None:
        await self.client.aclose()

    def parse_pr_url(self, url: str) -> tuple[str, str, int]:
        return parse_pr_url(url)

    async def fetch_pr(self, url: str) -> GitHubPR:
        owner, repo, number = self.parse_pr_url(url)
        return await self.fetch_parsed_pr(owner, repo, number)

    async def fetch_parsed_pr(self, owner: str, repo: str, number: int) -> GitHubPR:
        logger.info(
            "GitHub API 调用",
            extra={
                "props": {
                    "owner": owner,
                    "repo": repo,
                    "number": number,
                }
            },
        )

        try:
            pr_data = await self.client.get_json(f"/repos/{owner}/{repo}/pulls/{number}")
            files_data = await self.client.get_paginated_json(
                f"/repos/{owner}/{repo}/pulls/{number}/files"
            )
        except httpx.RequestError as exc:
            error_type = self.client.classify_request_error(exc)
            logger.warning(
                "GitHub API 连接失败",
                extra={
                    "props": {
                        "owner": owner,
                        "repo": repo,
                        "number": number,
                        "error_type": error_type,
                    }
                },
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": f"github_{error_type}",
                    "message": GITHUB_NETWORK_ERROR_MESSAGES[error_type],
                },
            ) from exc

        logger.info(
            "GitHub API 完成",
            extra={
                "props": {
                    "owner": owner,
                    "repo": repo,
                    "files": pr_data["changed_files"],
                }
            },
        )
        return map_github_pr_response(owner, repo, number, pr_data, files_data)

    async def fetch_compare(
        self, owner: str, repo: str, base_sha: str, head_sha: str
    ) -> list[dict[str, object]]:
        """Fetch files changed between two commits via GitHub Compare API."""
        try:
            data = await self.client.get_json(
                f"/repos/{owner}/{repo}/compare/{base_sha}...{head_sha}"
            )
            files = data.get("files", [])
            return [
                {
                    "filename": f.get("filename", ""),
                    "status": f.get("status", "modified"),
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "changes": f.get("changes", 0),
                    "patch": f.get("patch"),
                }
                for f in files
                if isinstance(f, dict)
            ]
        except Exception:
            logger.debug("Compare API failed for %s...%s", base_sha[:8], head_sha[:8], exc_info=True)
            return []

    async def fetch_discussion(
        self, owner: str, repo: str, number: int
    ) -> PRDiscussion:
        """Fetch PR body + recent issue comments + review comments."""
        issue_comments: list[PRComment] = []
        review_comments: list[PRComment] = []
        pr_body: str | None = None

        # fetch PR body from the PR endpoint
        try:
            pr_data = await self.client.get_json(
                f"/repos/{owner}/{repo}/pulls/{number}"
            )
            pr_body = pr_data.get("body")
        except Exception:
            logger.debug("Failed to fetch PR body for discussion", exc_info=True)

        # fetch issue comments (PR-level discussion)
        try:
            raw = await self.client.get_paginated_json(
                f"/repos/{owner}/{repo}/issues/{number}/comments"
            )
            issue_comments = [
                PRComment(
                    author=c.get("user", {}).get("login", "unknown"),
                    body=c.get("body", ""),
                    created_at=c.get("created_at", ""),
                )
                for c in raw[-50:]  # latest 50 (Phase 2: enough for LLM summarization)
            ]
        except Exception:
            logger.debug("Failed to fetch issue comments", exc_info=True)

        # fetch review comments (inline diff comments)
        try:
            raw = await self.client.get_paginated_json(
                f"/repos/{owner}/{repo}/pulls/{number}/comments"
            )
            review_comments = [
                PRComment(
                    author=c.get("user", {}).get("login", "unknown"),
                    body=c.get("body", ""),
                    created_at=c.get("created_at", ""),
                )
                for c in raw[-50:]  # latest 50
            ]
        except Exception:
            logger.debug("Failed to fetch review comments", exc_info=True)

        return PRDiscussion(
            pr_body=pr_body,
            issue_comments=issue_comments,
            review_comments=review_comments,
        )
