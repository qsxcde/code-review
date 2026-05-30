from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import require_jwt_user
from app.schemas.review_history import (
    FeedbackOut,
    FeedbackRequest,
    ReviewRecordDetail,
    ReviewRecordListResponse,
)
from app.services.review.history import add_feedback, delete_record, get_record_detail, list_records

router = APIRouter(prefix="/review", tags=["review_history"])


@router.get("/records", response_model=ReviewRecordListResponse)
async def get_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, alias="page_size"),
    status_filter: str | None = Query(default=None, alias="status"),
    owner: str | None = Query(default=None),
    repo: str | None = Query(default=None),
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRecordListResponse:
    return await list_records(
        db, user_id,
        page=page, page_size=page_size,
        status=status_filter, owner=owner, repo=repo,
    )


@router.get("/records/{record_id}", response_model=ReviewRecordDetail)
async def get_record(
    record_id: int,
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRecordDetail:
    return await get_record_detail(db, record_id, user_id)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_record(
    record_id: int,
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_record(db, record_id, user_id)


@router.post("/records/{record_id}/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    record_id: int,
    request: FeedbackRequest,
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackOut:
    return await add_feedback(
        db, record_id, user_id,
        request.risk_index, request.rating, request.comment,
    )
