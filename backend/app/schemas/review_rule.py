from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RuleFileFilters(BaseModel):
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class ReviewRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    category: Literal["security", "performance", "style", "custom"] = "custom"
    prompt_content: str = Field(min_length=1, max_length=4096)
    file_filters: RuleFileFilters | None = None
    priority: int = Field(default=0, ge=0, le=100)


class ReviewRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    category: Literal["security", "performance", "style", "custom"] | None = None
    prompt_content: str | None = Field(default=None, min_length=1, max_length=4096)
    file_filters: RuleFileFilters | None = None
    is_enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=100)


class ReviewRuleOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None = None
    category: str
    prompt_content: str
    file_filters: RuleFileFilters | None = None
    is_enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewRuleListResponse(BaseModel):
    items: list[ReviewRuleOut]
    total: int
