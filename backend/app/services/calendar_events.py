import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.calendar_event import CalendarEvent
from app.models.enums import CalendarEventType
from app.models.team import Team
from app.models.user import User
from app.schemas.calendar_event import (
    CalendarEventCreate,
    CalendarEventRead,
    CalendarEventUpdate,
)


def _validate_dates(start: dt.datetime, end: dt.datetime) -> None:
    if end < start:
        raise HTTPException(
            status_code=422, detail="end_datetime must not be before start_datetime"
        )


def _get_team_or_404(db: Session, team_id: int) -> None:
    if db.get(Team, team_id) is None:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")


def _get_user_or_404(db: Session, user_id: int) -> None:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")


def _get_activity_or_404(db: Session, activity_id: int) -> None:
    if db.get(Activity, activity_id) is None:
        raise HTTPException(status_code=404, detail=f"Activity {activity_id} not found")


def list_calendar_events(
    db: Session,
    project_id: int | None = None,
    team_id: int | None = None,
    event_type: CalendarEventType | None = None,
    date_from: dt.datetime | None = None,
    date_to: dt.datetime | None = None,
    q: str | None = None,
) -> list[CalendarEventRead]:
    stmt = select(CalendarEvent)
    if project_id is not None:
        stmt = stmt.where(CalendarEvent.project_id == project_id)
    if team_id is not None:
        stmt = stmt.where(CalendarEvent.team_id == team_id)
    if event_type is not None:
        stmt = stmt.where(CalendarEvent.event_type == event_type)
    if date_from is not None:
        stmt = stmt.where(CalendarEvent.end_datetime >= date_from)
    if date_to is not None:
        stmt = stmt.where(CalendarEvent.start_datetime <= date_to)
    if q:
        stmt = stmt.where(CalendarEvent.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(CalendarEvent.start_datetime)
    events = db.scalars(stmt).all()
    return [CalendarEventRead.model_validate(e) for e in events]


def get_calendar_event(db: Session, event_id: int) -> CalendarEventRead:
    event = db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return CalendarEventRead.model_validate(event)


def create_calendar_event(
    db: Session, payload: CalendarEventCreate
) -> CalendarEventRead:
    _validate_dates(payload.start_datetime, payload.end_datetime)
    if payload.team_id is not None:
        _get_team_or_404(db, payload.team_id)
    if payload.owner_user_id is not None:
        _get_user_or_404(db, payload.owner_user_id)
    if payload.related_activity_id is not None:
        _get_activity_or_404(db, payload.related_activity_id)

    event = CalendarEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return CalendarEventRead.model_validate(event)


def update_calendar_event(
    db: Session, event_id: int, payload: CalendarEventUpdate
) -> CalendarEventRead:
    event = db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")

    data = payload.model_dump(exclude_unset=True)
    new_start = data.get("start_datetime", event.start_datetime)
    new_end = data.get("end_datetime", event.end_datetime)
    _validate_dates(new_start, new_end)

    if data.get("team_id") is not None:
        _get_team_or_404(db, data["team_id"])
    if data.get("owner_user_id") is not None:
        _get_user_or_404(db, data["owner_user_id"])
    if data.get("related_activity_id") is not None:
        _get_activity_or_404(db, data["related_activity_id"])

    for field, value in data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return CalendarEventRead.model_validate(event)


def delete_calendar_event(db: Session, event_id: int) -> None:
    event = db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    db.delete(event)
    db.commit()
