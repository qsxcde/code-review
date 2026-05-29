from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ReviewFileInput(BaseModel):
    filename: str
    status: str = "modified"
    additions: int = 0
    deletions: int = 0
    patch: str


class MockReviewRequest(BaseModel):
    pr_url: HttpUrl = Field(alias="prUrl")
    title: str
    description: str | None = None
    author: str | None = None
    base_branch: str | None = Field(default=None, alias="baseBranch")
    head_branch: str | None = Field(default=None, alias="headBranch")
    files: list[ReviewFileInput]

    model_config = ConfigDict(populate_by_name=True)


class RiskItem(BaseModel):
    file: str
    line: int | None = None
    severity: Literal["high", "medium", "low"]
    category: str
    issue: str
    impact: str
    suggestion: str
    confidence: float = Field(ge=0, le=1)


class ReviewSuggestion(BaseModel):
    file: str
    type: Literal["must_fix", "should_fix", "nice_to_have"]
    comment: str


class ReviewSummary(BaseModel):
    overview: str
    changedModules: list[str]
    impact: list[str]


class ReviewMetrics(BaseModel):
    highRiskCount: int
    mediumRiskCount: int
    lowRiskCount: int
    analyzedFileCount: int


class ReviewResult(BaseModel):
    summary: ReviewSummary
    risks: list[RiskItem]
    suggestions: list[ReviewSuggestion]
    metrics: ReviewMetrics

