import datetime as dt

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import MilestoneStatus


class Milestone(TimestampMixin, Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(String(4000))
    date: Mapped[dt.date] = mapped_column(Date)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus), default=MilestoneStatus.NOT_STARTED
    )

    project: Mapped["Project"] = relationship(back_populates="milestones")  # noqa: F821
    team: Mapped["Team | None"] = relationship()  # noqa: F821
    owner_user: Mapped["User | None"] = relationship()  # noqa: F821
