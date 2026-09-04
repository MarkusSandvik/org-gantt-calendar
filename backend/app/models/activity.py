import datetime as dt

from sqlalchemy import Date, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ActivityStatus, Priority


class Activity(TimestampMixin, Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(String(4000))
    start_date: Mapped[dt.date] = mapped_column(Date)
    end_date: Mapped[dt.date] = mapped_column(Date)
    status: Mapped[ActivityStatus] = mapped_column(
        Enum(ActivityStatus), default=ActivityStatus.NOT_STARTED
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.NORMAL)
    owner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    project: Mapped["Project"] = relationship(back_populates="activities")  # noqa: F821
    owner_team: Mapped["Team | None"] = relationship(foreign_keys=[owner_team_id])  # noqa: F821
    owner_user: Mapped["User | None"] = relationship(foreign_keys=[owner_user_id])  # noqa: F821
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_id])  # noqa: F821
    contributors: Mapped[list["ActivityContributor"]] = relationship(
        back_populates="activity"
    )


class ActivityContributor(Base):
    __tablename__ = "activity_contributors"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    activity: Mapped["Activity"] = relationship(back_populates="contributors")
    user: Mapped["User"] = relationship()  # noqa: F821
