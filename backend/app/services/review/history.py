import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.models.review_record import ReviewRecord
from app.schemas.review import ReviewAnalyzeResponse
from app.schemas.review_history import FeedbackOut, ReviewRecordDetail, ReviewRecordListResponse, ReviewRecordOut

logger = logging.getLogger(__name__)

DUPLICATE_ENTRY_ERRNO = 1062


def _record_to_out(record: ReviewRecord) -> ReviewRecordOut:
    return ReviewRecordOut(
        id=record.id,
        pr_url=record.pr_url,
        pr_title=record.pr_title,
        owner=record.owner,
        repo=record.repo,
        pr_number=record.pr_number,
        status=record.status,
        file_count=record.file_count or 0,
        risk_counts=record.risk_counts,
        duration_ms=record.duration_ms,
        created_at=record.created_at,
        completed_at=record.completed_at,
    )


def _record_to_detail(record: ReviewRecord) -> ReviewRecordDetail:
    return ReviewRecordDetail(
        id=record.id,
        pr_url=record.pr_url,
        pr_title=record.pr_title,
        owner=record.owner,
        repo=record.repo,
        pr_number=record.pr_number,
        status=record.status,
        file_count=record.file_count or 0,
        risk_counts=record.risk_counts,
        duration_ms=record.duration_ms,
        created_at=record.created_at,
        completed_at=record.completed_at,
        summary_json=record.summary_json,
        result_json=record.result_json,
    )


async def find_cached_record(
    db: AsyncSession, user_id: int, pr_sha: str
) -> ReviewAnalyzeResponse | None:
    if not pr_sha:
        return None
    result = await db.execute(
        select(ReviewRecord)
        .where(
            ReviewRecord.user_id == user_id,
            ReviewRecord.pr_sha == pr_sha,
            ReviewRecord.status == "completed",
        )
        .order_by(desc(ReviewRecord.created_at))
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None or record.result_json is None:
        return None
    return ReviewAnalyzeResponse.model_validate(record.result_json)


async def create_pending_record(
    db: AsyncSession,
    user_id: int,
    pr_url: str,
    pr_title: str,
    owner: str,
    repo: str,
    pr_number: int,
    pr_sha: str,
) -> int:
    record = ReviewRecord(
        user_id=user_id,
        pr_url=pr_url,
        pr_title=pr_title,
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        pr_sha=pr_sha,
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record.id


async def save_completed_record(
    db: AsyncSession,
    record_id: int,
    response: ReviewAnalyzeResponse,
) -> None:
    result = await db.execute(select(ReviewRecord).where(ReviewRecord.id == record_id))
    record = result.scalar_one_or_none()
    if record is None:
        logger.error("Record %s not found for completion update", record_id)
        return

    analysis = response.analysis
    pr = response.pr

    record.status = "completed"
    record.summary_json = analysis.summary.model_dump()
    record.result_json = response.model_dump()
    record.file_count = pr.changedFiles
    record.risk_counts = {
        "high": analysis.metrics.highRiskCount,
        "medium": analysis.metrics.mediumRiskCount,
        "low": analysis.metrics.lowRiskCount,
    }
    record.duration_ms = response.durationMs
    record.completed_at = datetime.utcnow()
    await db.commit()


async def save_failed_record(db: AsyncSession, record_id: int) -> None:
    result = await db.execute(select(ReviewRecord).where(ReviewRecord.id == record_id))
    record = result.scalar_one_or_none()
    if record is not None:
        record.status = "failed"
        record.completed_at = datetime.utcnow()
        await db.commit()


async def list_records(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
) -> ReviewRecordListResponse:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    query = select(ReviewRecord).where(ReviewRecord.user_id == user_id)
    count_query = select(func.count(ReviewRecord.id)).where(ReviewRecord.user_id == user_id)

    if status:
        query = query.where(ReviewRecord.status == status)
        count_query = count_query.where(ReviewRecord.status == status)
    if owner:
        query = query.where(ReviewRecord.owner == owner)
        count_query = count_query.where(ReviewRecord.owner == owner)
    if repo:
        query = query.where(ReviewRecord.repo == repo)
        count_query = count_query.where(ReviewRecord.repo == repo)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(ReviewRecord.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    records = result.scalars().all()

    return ReviewRecordListResponse(
        items=[_record_to_out(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_record_detail(
    db: AsyncSession, record_id: int, user_id: int
) -> ReviewRecordDetail:
    result = await db.execute(
        select(ReviewRecord).where(
            ReviewRecord.id == record_id, ReviewRecord.user_id == user_id
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review record not found",
        )
    return _record_to_detail(record)


async def delete_record(db: AsyncSession, record_id: int, user_id: int) -> None:
    result = await db.execute(
        select(ReviewRecord).where(
            ReviewRecord.id == record_id, ReviewRecord.user_id == user_id
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review record not found",
        )
    await db.delete(record)
    await db.commit()


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
