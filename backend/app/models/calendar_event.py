import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import CalendarEventType, RecurrenceFrequency


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
    all_teams: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    related_activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id"))
    # A recurring event is materialized as one CalendarEvent row per
    # occurrence (not expanded virtually at read time) — the simplest fit
    # for this already-flat model. recurrence_frequency/recurrence_end_date
    # are only meaningful on the series leader (see services/calendar_events
    # .py); every occurrence, leader included, carries recurrence_group_id
    # equal to the leader's own id, which is how "delete this and future" is
    # implemented. Replaces the unused, never-wired recurrence_rule column
    # from Phase 7 (see CHANGELOG.md) — an RRULE-style string was never
    # needed for the fixed set of frequencies this app actually offers.
    recurrence_frequency: Mapped[RecurrenceFrequency | None] = mapped_column(
        Enum(RecurrenceFrequency)
    )
    recurrence_end_date: Mapped[dt.date | None] = mapped_column(Date)
    recurrence_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("calendar_events.id", use_alter=True, name="fk_calendar_events_recurrence_group_id")
    )

    project: Mapped["Project"] = relationship(back_populates="calendar_events")  # noqa: F821
    team: Mapped["Team | None"] = relationship()  # noqa: F821
    owner_user: Mapped["User | None"] = relationship()  # noqa: F821
    related_activity: Mapped["Activity | None"] = relationship()  # noqa: F821
