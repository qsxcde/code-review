import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.redis import get_redis
from app.core.rate_limit import require_rate_limit
from app.core.security import require_jwt_user
from app.schemas.review import (
    MockReviewRequest,
    ReviewAnalyzeRequest,
    ReviewAnalyzeResponse,
    ReviewResult,
)
from app.services.github import get_github_pr_service
from app.services.llm import LLMReviewService
from app.services.review import ReviewAnalysisService

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/review",
    tags=["review"],
    dependencies=[Depends(require_jwt_user), Depends(require_rate_limit)],
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
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ReviewAnalyzeResponse:
    github_service = get_github_pr_service(
        token=settings.github_token,
        proxy=settings.github_api_proxy,
    )
    analysis_service = ReviewAnalysisService(github_service, settings)
    return await analysis_service.analyze(str(request.pr_url), user_id, db, redis)
