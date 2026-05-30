from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReviewRecordOut(BaseModel):
    id: int
    pr_url: str
    pr_title: str | None = None
    owner: str | None = None
    repo: str | None = None
    pr_number: int | None = None
    status: str
    file_count: int = 0
    risk_counts: dict | None = None
    duration_ms: int | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ReviewRecordDetail(ReviewRecordOut):
    summary_json: dict | None = None
    result_json: dict | None = None


class ReviewRecordListResponse(BaseModel):
    items: list[ReviewRecordOut]
    total: int
    page: int
    page_size: int


class FeedbackRequest(BaseModel):
    risk_index: int = Field(alias="risk_index")
    rating: Literal["helpful", "not_helpful", "false_positive"]
    comment: str | None = None


class FeedbackOut(BaseModel):
    id: int
    record_id: int
    risk_index: int
    rating: str
    comment: str | None = None
    created_at: datetime
