import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_record import ReviewRecord
from app.schemas.review import ReviewAnalyzeResponse
from app.schemas.review_history import ReviewRecordDetail, ReviewRecordListResponse, ReviewRecordOut

logger = logging.getLogger(__name__)


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
    db: AsyncSession, user_id: int, pr_sha: str, redis=None
) -> ReviewAnalyzeResponse | None:
    if not pr_sha:
        return None

    cache_key = f"hotcache:review:{user_id}:{pr_sha}"

    # L1: Redis
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return ReviewAnalyzeResponse.model_validate_json(cached)
        except Exception:
            pass

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
    response = ReviewAnalyzeResponse.model_validate(record.result_json)

    # Write back to Redis L1
    if redis and record is not None:
        try:
            await redis.setex(cache_key, 86400, response.model_dump_json())
        except Exception:
            pass

    return response


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


async def set_record_running(db: AsyncSession, record_id: int) -> None:
    """Mark a review record as running."""
    result = await db.execute(select(ReviewRecord).where(ReviewRecord.id == record_id))
    record = result.scalar_one_or_none()
    if record is not None:
        record.status = "running"
        await db.commit()


async def get_user_record(
    db: AsyncSession, record_id: int, user_id: int
) -> ReviewRecord | None:
    """Fetch a review record with ownership check."""
    result = await db.execute(
        select(ReviewRecord).where(
            ReviewRecord.id == record_id, ReviewRecord.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def save_completed_record(
    db: AsyncSession,
    record_id: int,
    response: ReviewAnalyzeResponse,
    analysis_mode: str = "single",
    redis=None,
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
    record.result_json = {
        **response.model_dump(),
        "analysis_mode": analysis_mode,
    }
    record.file_count = pr.changedFiles
    record.risk_counts = {
        "high": analysis.metrics.highRiskCount,
        "medium": analysis.metrics.mediumRiskCount,
        "low": analysis.metrics.lowRiskCount,
    }
    record.duration_ms = response.durationMs
    record.completed_at = datetime.now(timezone.utc)
    await db.commit()

    if redis:
        try:
            cache_key = f"hotcache:review:{record.user_id}:{record.pr_sha}"
            await redis.setex(cache_key, 86400, response.model_dump_json())
        except Exception:
            pass


async def save_failed_record(db: AsyncSession, record_id: int) -> None:
    result = await db.execute(select(ReviewRecord).where(ReviewRecord.id == record_id))
    record = result.scalar_one_or_none()
    if record is not None:
        record.status = "failed"
        record.completed_at = datetime.now(timezone.utc)
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
