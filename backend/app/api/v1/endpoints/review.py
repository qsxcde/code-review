from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.review import MockReviewRequest, ReviewResult
from app.services.llm_review import LLMReviewService

router = APIRouter(prefix="/review", tags=["review"])


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

