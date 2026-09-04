import datetime as dt

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import CalendarEventType


class CalendarEvent(TimestampMixin, Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(String(4000))
    event_type: Mapped[CalendarEventType] = mapped_column(Enum(CalendarEventType))
    start_datetime: Mapped[dt.datetime] = mapped_column(DateTime)
    end_datetime: Mapped[dt.datetime] = mapped_column(DateTime)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    location: Mapped[str | None] = mapped_column(String(300))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    related_activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id"))
    recurrence_rule: Mapped[str | None] = mapped_column(String(500))

    project: Mapped["Project"] = relationship(back_populates="calendar_events")  # noqa: F821
    team: Mapped["Team | None"] = relationship()  # noqa: F821
    owner_user: Mapped["User | None"] = relationship()  # noqa: F821
    related_activity: Mapped["Activity | None"] = relationship()  # noqa: F821
