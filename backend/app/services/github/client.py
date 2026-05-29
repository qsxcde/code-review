import logging
from collections.abc import Sequence
from typing import Any

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

GITHUB_NETWORK_ERROR_MESSAGES = {
    "timeout": "GitHub API request timed out",
    "proxy": "GitHub API proxy connection failed",
    "connection": "Unable to establish a connection to GitHub API",
    "network": "GitHub API network request failed",
}


class GitHubAPIClient:
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

    async def get_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._get_client().get(
            f"{self.base_url}{path}",
            headers=self._build_headers(),
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

    async def get_paginated_json(self, path: str) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []

        while True:
            response = await self._get_client().get(
                f"{self.base_url}{path}",
                headers=self._build_headers(),
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

    def classify_request_error(self, exc: httpx.RequestError) -> str:
        if isinstance(exc, httpx.TimeoutException):
            return "timeout"
        if isinstance(exc, httpx.ProxyError):
            return "proxy"
        if isinstance(exc, httpx.ConnectError):
            return "connection"
        return "network"

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=20, proxy=self.proxy)
        return self._client

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-code-review-backend",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

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
