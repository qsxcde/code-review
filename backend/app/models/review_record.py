from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    pr_url: Mapped[str] = mapped_column(String(512), nullable=False)
    pr_title: Mapped[str | None] = mapped_column(String(512))
    owner: Mapped[str | None] = mapped_column(String(128))
    repo: Mapped[str | None] = mapped_column(String(128))
    pr_number: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "completed", "failed"), default="pending"
    )
    summary_json: Mapped[dict | None] = mapped_column(JSON)
    result_json: Mapped[dict | None] = mapped_column(JSON)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_counts: Mapped[dict | None] = mapped_column(JSON)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    pr_sha: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
