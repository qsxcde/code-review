from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import require_jwt_user
from app.schemas.review_stats import ReviewStatsResponse
from app.services.review.feedback_service import get_review_stats

router = APIRouter(prefix="/review", tags=["review_stats"])


@router.get("/stats", response_model=ReviewStatsResponse)
async def review_stats(
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewStatsResponse:
    return await get_review_stats(db, user_id)
