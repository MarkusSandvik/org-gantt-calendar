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

    # Admin-configured starting filter for the Gantt and Calendar views (the
    # Settings admin tab) — applied only until a viewer picks their own
    # filter, never a restriction on what they can see. Gantt has no
    # "Organization only" filter state (see FilterBar), so it needs only a
    # team/tag pair; Calendar's own filter also distinguishes "no filter"
    # from "Organization only", hence the extra boolean there.
    #
    # use_alter=True: teams.project_id and tags.project_id already point
    # back at this table, so these four columns would otherwise create a
    # circular FK dependency between projects/teams/tags that SQLAlchemy
    # can't topologically sort for CREATE TABLE (harmless on SQLite, but a
    # real failure on stricter dialects like Postgres). use_alter defers
    # each of these to its own ALTER TABLE ADD CONSTRAINT after all three
    # tables exist, which breaks the cycle.
    default_gantt_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", use_alter=True, name="fk_projects_default_gantt_team_id_teams")
    )
    default_gantt_tag_id: Mapped[int | None] = mapped_column(
        ForeignKey("tags.id", use_alter=True, name="fk_projects_default_gantt_tag_id_tags")
    )
    default_calendar_all_teams: Mapped[bool] = mapped_column(Boolean, default=True)
    default_calendar_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", use_alter=True, name="fk_projects_default_calendar_team_id_teams")
    )
    default_calendar_tag_id: Mapped[int | None] = mapped_column(
        ForeignKey("tags.id", use_alter=True, name="fk_projects_default_calendar_tag_id_tags")
    )

    created_by: Mapped["User | None"] = relationship()  # noqa: F821
    # foreign_keys is required on both these and their Team.project/Tag.project
    # counterparts — the default_gantt_team_id/default_calendar_team_id (and
    # tag equivalents) above add extra FK paths between these two tables, so
    # SQLAlchemy can no longer infer which one this one-to-many is over.
    teams: Mapped[list["Team"]] = relationship(  # noqa: F821
        back_populates="project", foreign_keys="Team.project_id"
    )
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        back_populates="project", foreign_keys="Tag.project_id"
    )
    activities: Mapped[list["Activity"]] = relationship(back_populates="project")  # noqa: F821
    milestones: Mapped[list["Milestone"]] = relationship(back_populates="project")  # noqa: F821
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(back_populates="project")  # noqa: F821
    baselines: Mapped[list["Baseline"]] = relationship(back_populates="project")  # noqa: F821
    dependencies: Mapped[list["Dependency"]] = relationship(back_populates="project")  # noqa: F821
