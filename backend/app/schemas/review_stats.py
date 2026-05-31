from pydantic import BaseModel


class AgentFeedbackStats(BaseModel):
    agent: str
    total_risks: int = 0
    helpful: int = 0
    not_helpful: int = 0
    false_positive: int = 0
    false_positive_rate: float = 0.0


class RecentFalsePositive(BaseModel):
    record_id: int
    file: str
    issue: str
    created_at: str


class ReviewStatsResponse(BaseModel):
    total_analyses: int = 0
    total_risks_flagged: int = 0
    feedback_coverage: float = 0.0  # ratio: feedback_count / total_risks
    by_agent: list[AgentFeedbackStats] = []
    false_positive_rate: float = 0.0
    recent_false_positives: list[RecentFalsePositive] = []
