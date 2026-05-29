from typing import Any

from app.schemas.review import MockReviewRequest


def build_mock_review_payload(request: MockReviewRequest) -> dict[str, Any]:
    return {
        "prUrl": str(request.pr_url),
        "title": request.title,
        "description": request.description,
        "author": request.author,
        "baseBranch": request.base_branch,
        "headBranch": request.head_branch,
        "files": [file.model_dump() for file in request.files],
    }
