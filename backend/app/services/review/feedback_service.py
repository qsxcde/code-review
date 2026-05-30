import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.models.review_record import ReviewRecord
from app.schemas.review_history import FeedbackOut

logger = logging.getLogger(__name__)

DUPLICATE_ENTRY_ERRNO = 1062


async def add_feedback(
    db: AsyncSession,
    record_id: int,
    user_id: int,
    risk_index: int,
    rating: str,
    comment: str | None,
) -> FeedbackOut:
    result = await db.execute(
        select(ReviewRecord).where(
            ReviewRecord.id == record_id, ReviewRecord.user_id == user_id
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review record not found",
        )

    feedback_obj = Feedback(
        record_id=record_id,
        risk_index=risk_index,
        rating=rating,
        comment=comment,
    )
    db.add(feedback_obj)
    try:
        await db.commit()
        await db.refresh(feedback_obj)
    except IntegrityError as exc:
        await db.rollback()
        if exc.orig and getattr(exc.orig, "args", [None])[0] == DUPLICATE_ENTRY_ERRNO:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feedback already submitted for this risk item",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save feedback",
        )

    return FeedbackOut(
        id=feedback_obj.id,
        record_id=feedback_obj.record_id,
        risk_index=feedback_obj.risk_index,
        rating=feedback_obj.rating,
        comment=feedback_obj.comment,
        created_at=feedback_obj.created_at,
    )
