import datetime as dt

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ProjectStatus


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    season_label: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(2000))
    start_date: Mapped[dt.date | None] = mapped_column(Date)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    # Exactly one project should have this set at a time — the project the
    # org lands on by default (deep links to a specific project's slug
    # override this). Enforced in the service layer, not a DB constraint,
    # since SQLite can't express "at most one row where is_default" cleanly.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_scheduling_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    created_by: Mapped["User | None"] = relationship()  # noqa: F821
    teams: Mapped[list["Team"]] = relationship(back_populates="project")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship(back_populates="project")  # noqa: F821
    activities: Mapped[list["Activity"]] = relationship(back_populates="project")  # noqa: F821
    milestones: Mapped[list["Milestone"]] = relationship(back_populates="project")  # noqa: F821
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(back_populates="project")  # noqa: F821
    baselines: Mapped[list["Baseline"]] = relationship(back_populates="project")  # noqa: F821
    dependencies: Mapped[list["Dependency"]] = relationship(back_populates="project")  # noqa: F821
