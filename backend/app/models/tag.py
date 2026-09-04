import datetime as dt

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TaggableType


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(20))
    archived_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    project: Mapped["Project"] = relationship(back_populates="tags")  # noqa: F821


class TagAssociation(Base):
    """Polymorphic join: a tag applied to an activity, milestone, or calendar event."""

    __tablename__ = "tag_associations"

    id: Mapped[int] = mapped_column(primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"))
    entity_type: Mapped[TaggableType] = mapped_column(Enum(TaggableType))
    entity_id: Mapped[int] = mapped_column(Integer)

    tag: Mapped["Tag"] = relationship()
