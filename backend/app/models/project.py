import datetime as dt

from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(2000))
    start_date: Mapped[dt.date | None] = mapped_column(Date)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    auto_scheduling_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    teams: Mapped[list["Team"]] = relationship(back_populates="project")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship(back_populates="project")  # noqa: F821
    activities: Mapped[list["Activity"]] = relationship(back_populates="project")  # noqa: F821
    milestones: Mapped[list["Milestone"]] = relationship(back_populates="project")  # noqa: F821
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(back_populates="project")  # noqa: F821
    baselines: Mapped[list["Baseline"]] = relationship(back_populates="project")  # noqa: F821
