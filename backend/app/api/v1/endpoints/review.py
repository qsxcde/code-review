from fastapi import APIRouter, Depends

from app.agents.review import ReviewGraphRunner
from app.core.config import Settings, get_settings
from app.core.rate_limit import require_rate_limit
from app.core.security import require_api_token
from app.schemas.review import (
    MockReviewRequest,
    ReviewAnalyzeRequest,
    ReviewAnalyzeResponse,
    ReviewResult,
)
from app.services.github import get_github_pr_service
from app.services.llm import LLMReviewService

router = APIRouter(
    prefix="/review",
    tags=["review"],
    dependencies=[Depends(require_api_token), Depends(require_rate_limit)],
)


@router.post("/mock-analyze", response_model=ReviewResult)
async def analyze_mock_pr(
    request: MockReviewRequest,
    settings: Settings = Depends(get_settings),
) -> ReviewResult:
    service = LLMReviewService(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )
    return await service.analyze_mock_pr(request)


@router.post("/analyze", response_model=ReviewAnalyzeResponse)
async def analyze_pr(
    request: ReviewAnalyzeRequest,
    settings: Settings = Depends(get_settings),
) -> ReviewAnalyzeResponse:
    github_service = get_github_pr_service(
        token=settings.github_token,
        proxy=settings.github_api_proxy,
    )
    llm_service = LLMReviewService(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
    )
    graph = ReviewGraphRunner(github_service, llm_service)
    return await graph.analyze(str(request.pr_url))
