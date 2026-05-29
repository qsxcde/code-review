import logging
import re
from collections.abc import Sequence
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.schemas.github import GitHubPR, GitHubPRFile

logger = logging.getLogger(__name__)

GITHUB_PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)(?:[/?#].*)?$"
)

GITHUB_NETWORK_ERROR_MESSAGES = {
    "timeout": "GitHub API request timed out",
    "proxy": "GitHub API proxy connection failed",
    "connection": "Unable to establish a connection to GitHub API",
    "network": "GitHub API network request failed",
}


class GitHubPRService:
    def __init__(
        self,
        token: str | None = None,
        proxy: str | None = None,
    ) -> None:
        self.token = token
        self.proxy = proxy
        self.base_url = "https://api.github.com"
        self._client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=20, proxy=self.proxy)
        return self._client

    def parse_pr_url(self, url: str) -> tuple[str, str, int]:
        match = GITHUB_PR_URL_RE.match(url)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid GitHub PR URL",
            )

        return (
            match.group("owner"),
            match.group("repo"),
            int(match.group("number")),
        )

    async def fetch_pr(self, url: str) -> GitHubPR:
        owner, repo, number = self.parse_pr_url(url)
        headers = self._build_headers()
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
            pr_data = await self._get_json(
                f"/repos/{owner}/{repo}/pulls/{number}",
                headers,
            )
            files_data = await self._get_paginated_json(
                f"/repos/{owner}/{repo}/pulls/{number}/files",
                headers,
            )
        except httpx.RequestError as exc:
            error_type = self._classify_request_error(exc)
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
        return GitHubPR(
            owner=owner,
            repo=repo,
            number=number,
            title=pr_data["title"],
            body=pr_data.get("body"),
            state=pr_data["state"],
            author=pr_data["user"]["login"],
            html_url=pr_data["html_url"],
            base_branch=pr_data["base"]["ref"],
            head_branch=pr_data["head"]["ref"],
            changed_files=pr_data["changed_files"],
            additions=pr_data["additions"],
            deletions=pr_data["deletions"],
            files=[
                GitHubPRFile(
                    filename=file_data["filename"],
                    status=file_data["status"],
                    additions=file_data["additions"],
                    deletions=file_data["deletions"],
                    changes=file_data["changes"],
                    patch=file_data.get("patch"),
                )
                for file_data in files_data
            ],
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-code-review-backend",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    def _classify_request_error(self, exc: httpx.RequestError) -> str:
        if isinstance(exc, httpx.TimeoutException):
            return "timeout"
        if isinstance(exc, httpx.ProxyError):
            return "proxy"
        if isinstance(exc, httpx.ConnectError):
            return "connection"
        return "network"

    async def _get_json(
        self,
        path: str,
        headers: dict[str, str],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._get_client().get(
            f"{self.base_url}{path}",
            headers=headers,
            params=params,
        )
        self._raise_for_github_error(response)
        data = response.json()
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unexpected GitHub API response",
            )
        return data

    async def _get_paginated_json(
        self,
        path: str,
        headers: dict[str, str],
    ) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []

        while True:
            response = await self._get_client().get(
                f"{self.base_url}{path}",
                headers=headers,
                params={"page": page, "per_page": 100},
            )
            self._raise_for_github_error(response)
            data = response.json()
            if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unexpected GitHub API response",
                )

            page_items = [item for item in data if isinstance(item, dict)]
            items.extend(page_items)

            if len(page_items) < 100:
                return items
            page += 1

    def _raise_for_github_error(self, response: httpx.Response) -> None:
        if response.is_error:
            logger.warning(
                "github_api_error",
                extra={
                    "props": {
                        "event": "github_api_error",
                        "status_code": response.status_code,
                        "url_path": response.url.path,
                    }
                },
            )

        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GitHub PR not found or token has no access",
            )

        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub token",
            )

        if response.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="GitHub API access forbidden or rate limited",
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API request failed: {exc.response.status_code}",
            ) from exc


_github_services: dict[tuple[str | None, str | None], GitHubPRService] = {}


def get_github_pr_service(
    token: str | None = None,
    proxy: str | None = None,
) -> GitHubPRService:
    key = (token, proxy)
    if key not in _github_services:
        _github_services[key] = GitHubPRService(token=token, proxy=proxy)
    return _github_services[key]


async def close_github_pr_services() -> None:
    for service in _github_services.values():
        await service.aclose()
    _github_services.clear()
