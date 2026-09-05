import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core import permissions
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.calendar_event import CalendarEvent
from app.models.enums import CalendarEventType
from app.models.user import User
from app.schemas.calendar_event import (
    CalendarEventCreate,
    CalendarEventRead,
    CalendarEventUpdate,
)
from app.services import calendar_events as calendar_event_service

router = APIRouter(prefix="/calendar-events", tags=["calendar-events"])


def _get_event_or_404(db: Session, event_id: int) -> CalendarEvent:
    event = db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return event


@router.get("", response_model=list[CalendarEventRead])
def list_calendar_events(
    project_id: int | None = None,
    team_id: int | None = None,
    owner_user_id: int | None = None,
    event_type: CalendarEventType | None = None,
    date_from: dt.datetime | None = None,
    date_to: dt.datetime | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CalendarEventRead]:
    return calendar_event_service.list_calendar_events(
        db,
        project_id=project_id,
        team_id=team_id,
        owner_user_id=owner_user_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )


@router.get("/{event_id}", response_model=CalendarEventRead)
def get_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarEventRead:
    return calendar_event_service.get_calendar_event(db, event_id)


@router.post("", response_model=CalendarEventRead, status_code=201)
def create_calendar_event(
    payload: CalendarEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarEventRead:
    permissions.require(
        permissions.can_manage_calendar_event_for_team(db, current_user, payload.team_id)
    )
    return calendar_event_service.create_calendar_event(db, payload)


@router.patch("/{event_id}", response_model=CalendarEventRead)
def update_calendar_event(
    event_id: int,
    payload: CalendarEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarEventRead:
    event = _get_event_or_404(db, event_id)
    permissions.require(permissions.can_manage_calendar_event(db, current_user, event))
    return calendar_event_service.update_calendar_event(db, event_id, payload)


@router.delete("/{event_id}", status_code=204)
def delete_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    event = _get_event_or_404(db, event_id)
    permissions.require(permissions.can_manage_calendar_event(db, current_user, event))
    calendar_event_service.delete_calendar_event(db, event_id)
    return Response(status_code=204)
