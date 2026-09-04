import datetime as dt

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CommentableType


class Attachment(Base):
    """v0.1: external links only, no file upload/storage."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[CommentableType] = mapped_column(Enum(CommentableType))
    entity_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(2000))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC)
    )

    created_by: Mapped["User"] = relationship()  # noqa: F821
