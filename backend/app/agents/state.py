from typing import Any, TypedDict

from app.schemas.github import GitHubPR
from app.schemas.review import ReviewAnalyzeResponse, ReviewResult


class ReviewState(TypedDict, total=False):
    pr_url: str
    owner: str
    repo: str
    pull_number: int
    pr_data: GitHubPR
    context: dict[str, Any]
    analyzed_file_count: int
    analysis: ReviewResult
    response: ReviewAnalyzeResponse
    errors: list[str]
    started_at: float
