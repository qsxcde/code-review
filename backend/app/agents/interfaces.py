"""Abstract interfaces for agent → service decoupling.

Agent modules depend on these Protocols, not on concrete service classes.
Service classes (LLMReviewService, GitHubPRService) structurally satisfy
these protocols without explicit inheritance.
"""

from typing import Any, Protocol

from app.schemas.github import GitHubPR
from app.schemas.review import ReviewResult


class LLMProvider(Protocol):
    """Interface for LLM analysis services consumed by agent code."""

    async def analyze_payload(
        self,
        payload: dict[str, Any],
        system_prompt: str | None = None,
        stage: str | None = None,
    ) -> ReviewResult: ...

    async def analyze_json_payload(
        self,
        payload: dict[str, Any],
        system_prompt: str,
        stage: str | None = None,
    ) -> dict[str, Any]: ...


class GitHubProvider(Protocol):
    """Interface for GitHub PR services consumed by agent code."""

    def parse_pr_url(self, url: str) -> tuple[str, str, int]: ...

    async def fetch_pr(self, url: str) -> GitHubPR: ...

    async def fetch_parsed_pr(
        self, owner: str, repo: str, number: int
    ) -> GitHubPR: ...


class GitHubContentClient(Protocol):
    """Interface for the GitHub API client used by context enhancement."""

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str
    ) -> str | None: ...
