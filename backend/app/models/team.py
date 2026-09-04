import datetime as dt

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import TeamCategory


class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[TeamCategory] = mapped_column(Enum(TeamCategory))
    color: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    archived_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    project: Mapped["Project"] = relationship(back_populates="teams")  # noqa: F821
    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="team")


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    team: Mapped["Team"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="team_memberships")  # noqa: F821
