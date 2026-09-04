import datetime as dt

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CommentableType


class Comment(Base):
    """Append-only activity log entry. Never edited or overwritten."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[CommentableType] = mapped_column(Enum(CommentableType))
    entity_id: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(String(4000))
    created_at: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC)
    )
    # Plain strings, not an Enum column: this entry may record either an
    # ActivityStatus or a MilestoneStatus transition, and those are two
    # different enums with non-overlapping values (e.g. "at_risk" only
    # exists on MilestoneStatus).
    status_change_from: Mapped[str | None] = mapped_column(String(30))
    status_change_to: Mapped[str | None] = mapped_column(String(30))

    author: Mapped["User"] = relationship()  # noqa: F821
