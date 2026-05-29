import logging

import httpx
from fastapi import HTTPException, status

from app.schemas.github import GitHubPR
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
            "github_pr_fetch_started",
            extra={
                "props": {
                    "event": "github_pr_fetch_started",
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
                "github_api_connection_failed",
                extra={
                    "props": {
                        "event": "github_api_connection_failed",
                        "owner": owner,
                        "repo": repo,
                        "number": number,
                        "error_type": error_type,
                        "exception_type": exc.__class__.__name__,
                        "error_message": str(exc)[:300],
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
            "github_pr_fetch_completed",
            extra={
                "props": {
                    "event": "github_pr_fetch_completed",
                    "owner": owner,
                    "repo": repo,
                    "number": number,
                    "changed_files": pr_data["changed_files"],
                }
            },
        )
        return map_github_pr_response(owner, repo, number, pr_data, files_data)
