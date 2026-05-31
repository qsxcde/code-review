from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.feedback import Feedback  # noqa: E402, F401
from app.models.review_record import ReviewRecord  # noqa: E402, F401
from app.models.review_rule import ReviewRule  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

__all__ = ["Base", "Feedback", "ReviewRecord", "ReviewRule", "User"]
