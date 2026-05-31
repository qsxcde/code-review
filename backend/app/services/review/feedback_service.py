import logging
import re

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.models.review_record import ReviewRecord
from app.schemas.review_history import FeedbackOut
from app.schemas.review_stats import (
    AgentFeedbackStats,
    RecentFalsePositive,
    ReviewStatsResponse,
)

logger = logging.getLogger(__name__)

DUPLICATE_ENTRY_ERRNO = 1062

AGENT_PREFIX_RE = re.compile(r"^\[(安全|性能|风格)\]")


def _extract_agent(issue: str) -> str:
    m = AGENT_PREFIX_RE.match(issue)
    return m.group(1) if m else "通用"


def _parse_risk(record: ReviewRecord, risk_index: int) -> dict | None:
    """Extract a specific risk from a review record's result_json."""
    try:
        if not record.result_json:
            return None
        risks = record.result_json.get("analysis", {}).get("risks", [])
        if risk_index < 0 or risk_index >= len(risks):
            return None
        return risks[risk_index]
    except Exception:
        return None


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


async def get_review_stats(
    db: AsyncSession, user_id: int
) -> ReviewStatsResponse:
    """Aggregate feedback stats per agent for a user."""
    records_result = await db.execute(
        select(ReviewRecord).where(
            ReviewRecord.user_id == user_id,
            ReviewRecord.status == "completed",
        )
    )
    records = records_result.scalars().all()

    feedback_result = await db.execute(
        select(Feedback).where(
            Feedback.record_id.in_(
                select(ReviewRecord.id).where(ReviewRecord.user_id == user_id)
            )
        )
    )
    feedbacks = feedback_result.scalars().all()

    # map feedback by record_id → risk_index for fast lookup
    feedback_map: dict[tuple[int, int], Feedback] = {
        (f.record_id, f.risk_index): f for f in feedbacks
    }

    agent_stats: dict[str, dict[str, int]] = {}
    total_risks = 0
    feedback_count = 0
    recent_fps: list[RecentFalsePositive] = []

    for record in records:
        risks = record.result_json.get("analysis", {}).get("risks", []) if record.result_json else []
        total_risks += len(risks)
        for idx, risk in enumerate(risks):
            agent = _extract_agent(risk.get("issue", ""))
            if agent not in agent_stats:
                agent_stats[agent] = {"total": 0, "helpful": 0, "not_helpful": 0, "false_positive": 0}
            agent_stats[agent]["total"] += 1

            fb = feedback_map.get((record.id, idx))
            if fb:
                feedback_count += 1
                agent_stats[agent][fb.rating] = agent_stats[agent].get(fb.rating, 0) + 1
                if fb.rating == "false_positive":
                    recent_fps.append(RecentFalsePositive(
                        record_id=record.id,
                        file=risk.get("file", ""),
                        issue=risk.get("issue", ""),
                        created_at=str(record.created_at or ""),
                    ))

    by_agent = []
    total_fp = 0
    for agent, counts in sorted(agent_stats.items()):
        fp_rate = counts["false_positive"] / counts["total"] if counts["total"] > 0 else 0
        total_fp += counts["false_positive"]
        by_agent.append(AgentFeedbackStats(
            agent=agent,
            total_risks=counts["total"],
            helpful=counts.get("helpful", 0),
            not_helpful=counts.get("not_helpful", 0),
            false_positive=counts.get("false_positive", 0),
            false_positive_rate=round(fp_rate, 3),
        ))

    return ReviewStatsResponse(
        total_analyses=len(records),
        total_risks_flagged=total_risks,
        feedback_coverage=round(feedback_count / total_risks, 3) if total_risks > 0 else 0,
        by_agent=by_agent,
        false_positive_rate=round(total_fp / total_risks, 3) if total_risks > 0 else 0,
        recent_false_positives=sorted(recent_fps, key=lambda x: x.created_at, reverse=True)[:10],
    )


async def get_helpful_examples(
    db: AsyncSession, user_id: int, agent_category: str, limit: int = 5
) -> list[dict]:
    """Return top helpful feedback items for few-shot prompt injection."""
    result = await db.execute(
        select(Feedback)
        .join(ReviewRecord, Feedback.record_id == ReviewRecord.id)
        .where(
            ReviewRecord.user_id == user_id,
            Feedback.rating == "helpful",
        )
        .order_by(desc(Feedback.created_at))
        .limit(limit * 3)  # fetch extra, filter by agent after
    )
    feedbacks = result.scalars().all()

    examples: list[dict] = []
    for fb in feedbacks:
        if len(examples) >= limit:
            break
        record_result = await db.execute(
            select(ReviewRecord).where(ReviewRecord.id == fb.record_id)
        )
        record = record_result.scalar_one_or_none()
        risk = _parse_risk(record, fb.risk_index) if record else None
        if risk is None:
            continue
        agent = _extract_agent(risk.get("issue", ""))
        if agent != agent_category and agent_category not in ("custom", "通用"):
            continue
        examples.append({
            "file": risk.get("file", ""),
            "line": risk.get("line"),
            "issue": risk.get("issue", ""),
            "suggestion": risk.get("suggestion", ""),
        })
    return examples
