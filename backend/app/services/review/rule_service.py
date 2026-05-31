"""CRUD service for custom review rules."""

import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_rule import ReviewRule
from app.schemas.review_rule import (
    ReviewRuleCreate,
    ReviewRuleListResponse,
    ReviewRuleOut,
    ReviewRuleUpdate,
)

logger = logging.getLogger(__name__)


def _to_out(rule: ReviewRule) -> ReviewRuleOut:
    return ReviewRuleOut.model_validate(rule)


async def create_rule(
    db: AsyncSession, user_id: int, data: ReviewRuleCreate
) -> ReviewRuleOut:
    rule = ReviewRule(
        user_id=user_id,
        name=data.name,
        description=data.description,
        category=data.category,
        prompt_content=data.prompt_content,
        file_filters=data.file_filters.model_dump() if data.file_filters else None,
        priority=data.priority,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _to_out(rule)


async def list_rules(
    db: AsyncSession,
    user_id: int,
    category: str | None = None,
) -> ReviewRuleListResponse:
    query = select(ReviewRule).where(ReviewRule.user_id == user_id)
    count_query = select(func.count(ReviewRule.id)).where(ReviewRule.user_id == user_id)

    if category:
        query = query.where(ReviewRule.category == category)
        count_query = count_query.where(ReviewRule.category == category)

    query = query.order_by(ReviewRule.priority.desc(), ReviewRule.created_at.desc())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(query)
    rules = result.scalars().all()

    return ReviewRuleListResponse(
        items=[_to_out(r) for r in rules],
        total=total,
    )


async def get_rule(db: AsyncSession, rule_id: int, user_id: int) -> ReviewRuleOut:
    result = await db.execute(
        select(ReviewRule).where(
            ReviewRule.id == rule_id,
            ReviewRule.user_id == user_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review rule not found",
        )
    return _to_out(rule)


async def update_rule(
    db: AsyncSession, rule_id: int, user_id: int, data: ReviewRuleUpdate
) -> ReviewRuleOut:
    result = await db.execute(
        select(ReviewRule).where(
            ReviewRule.id == rule_id,
            ReviewRule.user_id == user_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review rule not found",
        )

    update_dict = data.model_dump(exclude_unset=True)
    if "file_filters" in update_dict and update_dict["file_filters"] is not None:
        update_dict["file_filters"] = update_dict["file_filters"].model_dump()

    for key, value in update_dict.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return _to_out(rule)


async def delete_rule(db: AsyncSession, rule_id: int, user_id: int) -> None:
    result = await db.execute(
        select(ReviewRule).where(
            ReviewRule.id == rule_id,
            ReviewRule.user_id == user_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review rule not found",
        )
    await db.delete(rule)
    await db.commit()


async def get_enabled_rules(
    db: AsyncSession, user_id: int
) -> list[ReviewRuleOut]:
    """Get all enabled rules for a user (used during analysis)."""
    result = await db.execute(
        select(ReviewRule)
        .where(
            ReviewRule.user_id == user_id,
            ReviewRule.is_enabled == True,  # noqa: E712
        )
        .order_by(ReviewRule.priority.desc())
    )
    rules = result.scalars().all()
    return [_to_out(r) for r in rules]
