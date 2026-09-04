import datetime as dt

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Baseline(Base):
    """An immutable snapshot of the planned schedule at a point in time.
    Never overwritten; multiple baselines may coexist for one project."""

    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(String(2000))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC)
    )

    project: Mapped["Project"] = relationship(back_populates="baselines")  # noqa: F821
    activity_snapshots: Mapped[list["BaselineActivity"]] = relationship(
        back_populates="baseline"
    )
    milestone_snapshots: Mapped[list["BaselineMilestone"]] = relationship(
        back_populates="baseline"
    )


class BaselineActivity(Base):
    __tablename__ = "baseline_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    baseline_id: Mapped[int] = mapped_column(ForeignKey("baselines.id"))
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"))
    planned_start_date: Mapped[dt.date] = mapped_column(Date)
    planned_end_date: Mapped[dt.date] = mapped_column(Date)

    baseline: Mapped["Baseline"] = relationship(back_populates="activity_snapshots")
    activity: Mapped["Activity"] = relationship()  # noqa: F821


class BaselineMilestone(Base):
    __tablename__ = "baseline_milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    baseline_id: Mapped[int] = mapped_column(ForeignKey("baselines.id"))
    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id"))
    planned_date: Mapped[dt.date] = mapped_column(Date)

    baseline: Mapped["Baseline"] = relationship(back_populates="milestone_snapshots")
    milestone: Mapped["Milestone"] = relationship()  # noqa: F821
