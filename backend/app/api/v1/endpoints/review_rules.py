from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import require_jwt_user
from app.schemas.review_rule import (
    ReviewRuleCreate,
    ReviewRuleListResponse,
    ReviewRuleOut,
    ReviewRuleUpdate,
)
from app.services.review.rule_service import (
    create_rule,
    delete_rule,
    get_rule,
    list_rules,
    update_rule,
)

router = APIRouter(prefix="/rules", tags=["review_rules"])


@router.post("", response_model=ReviewRuleOut, status_code=status.HTTP_201_CREATED)
async def create(
    data: ReviewRuleCreate,
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRuleOut:
    return await create_rule(db, user_id, data)


@router.get("", response_model=ReviewRuleListResponse)
async def list_all(
    category: str | None = Query(default=None),
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRuleListResponse:
    return await list_rules(db, user_id, category=category)


@router.get("/{rule_id}", response_model=ReviewRuleOut)
async def get_one(
    rule_id: int,
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRuleOut:
    return await get_rule(db, rule_id, user_id)


@router.put("/{rule_id}", response_model=ReviewRuleOut)
async def update(
    rule_id: int,
    data: ReviewRuleUpdate,
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRuleOut:
    return await update_rule(db, rule_id, user_id, data)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    rule_id: int,
    user_id: int = Depends(require_jwt_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_rule(db, rule_id, user_id)
