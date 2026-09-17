import calendar
import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.calendar_event import CalendarEvent
from app.models.enums import CalendarEventType, RecurrenceFrequency, TaggableType
from app.models.tag import Tag, TagAssociation
from app.models.team import Team
from app.models.user import User
from app.schemas.calendar_event import (
    CalendarEventActivityRead,
    CalendarEventCreate,
    CalendarEventRead,
    CalendarEventTagRead,
    CalendarEventTeamRead,
    CalendarEventUpdate,
    CalendarEventUserRead,
)
from app.services.projects import ensure_project_editable

# A safety cap, not a product limit — long enough for any realistic season
# (5 years of weekly events), just there so a mistyped end date decades out
# can't silently create thousands of rows.
MAX_RECURRENCE_OCCURRENCES = 260


def _add_months(value: dt.datetime, months: int) -> dt.datetime:
    total_month_index = value.month - 1 + months
    year = value.year + total_month_index // 12
    month = total_month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


_FIXED_STEP = {
    RecurrenceFrequency.DAILY: dt.timedelta(days=1),
    RecurrenceFrequency.WEEKLY: dt.timedelta(weeks=1),
    RecurrenceFrequency.BIWEEKLY: dt.timedelta(weeks=2),
}


def _generate_occurrence_starts(
    start: dt.datetime, frequency: RecurrenceFrequency, end_date: dt.date
) -> list[dt.datetime]:
    """The first element is always `start` itself — the series leader.

    Monthly occurrences are computed from `start`'s own day-of-month each
    time (occurrence N = start + N months), not by re-stepping from the
    previous occurrence — otherwise a start date of the 31st would clamp to
    the 28th in February and then never recover in months that do have a
    31st, permanently drifting the series' day-of-month one short month
    early instead of just skipping the months that don't have that day."""
    starts = [start]
    if frequency == RecurrenceFrequency.MONTHLY:
        month_offset = 0
        while True:
            month_offset += 1
            candidate = _add_months(start, month_offset)
            if candidate.date() > end_date:
                return starts
            starts.append(candidate)
            _check_occurrence_cap(starts)

    step = _FIXED_STEP[frequency]
    current = start
    while True:
        current = current + step
        if current.date() > end_date:
            return starts
        starts.append(current)
        _check_occurrence_cap(starts)


def _check_occurrence_cap(starts: list[dt.datetime]) -> None:
    if len(starts) > MAX_RECURRENCE_OCCURRENCES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"That repeat schedule would create more than "
                f"{MAX_RECURRENCE_OCCURRENCES} events — pick a shorter end date."
            ),
        )


def _validate_dates(start: dt.datetime, end: dt.datetime) -> None:
    if end < start:
        raise HTTPException(
            status_code=422, detail="end_datetime must not be before start_datetime"
        )


def _validate_team_scope(all_teams: bool, team_id: int | None) -> None:
    if all_teams and team_id is not None:
        raise HTTPException(
            status_code=422,
            detail="A calendar event can't have both a specific team and apply to the Organization.",
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


def _get_tags_or_404(db: Session, tag_ids: list[int]) -> None:
    if not tag_ids:
        return
    found_ids = set(db.scalars(select(Tag.id).where(Tag.id.in_(tag_ids))).all())
    missing = set(tag_ids) - found_ids
    if missing:
        raise HTTPException(status_code=404, detail=f"Tag(s) not found: {sorted(missing)}")


def _sync_tags(db: Session, event: CalendarEvent, tag_ids: list[int]) -> None:
    _get_tags_or_404(db, tag_ids)
    db.query(TagAssociation).filter(
        TagAssociation.entity_type == TaggableType.CALENDAR_EVENT,
        TagAssociation.entity_id == event.id,
    ).delete()
    for tid in tag_ids:
        db.add(
            TagAssociation(
                tag_id=tid, entity_type=TaggableType.CALENDAR_EVENT, entity_id=event.id
            )
        )


def _serialize(db: Session, event: CalendarEvent) -> CalendarEventRead:
    tag_rows = db.scalars(
        select(Tag)
        .join(TagAssociation, TagAssociation.tag_id == Tag.id)
        .where(
            TagAssociation.entity_type == TaggableType.CALENDAR_EVENT,
            TagAssociation.entity_id == event.id,
        )
        .order_by(Tag.name)
    ).all()
    return CalendarEventRead(
        id=event.id,
        project_id=event.project_id,
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        all_day=event.all_day,
        location=event.location,
        team=CalendarEventTeamRead.model_validate(event.team) if event.team else None,
        all_teams=event.all_teams,
        owner_user=CalendarEventUserRead.model_validate(event.owner_user)
        if event.owner_user
        else None,
        related_activity=CalendarEventActivityRead.model_validate(event.related_activity)
        if event.related_activity
        else None,
        tags=[CalendarEventTagRead.model_validate(t) for t in tag_rows],
        recurrence_frequency=event.recurrence_frequency,
        recurrence_end_date=event.recurrence_end_date,
        recurrence_group_id=event.recurrence_group_id,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def list_calendar_events(
    db: Session,
    project_id: int | None = None,
    team_id: int | None = None,
    all_teams_only: bool = False,
    owner_user_id: int | None = None,
    event_type: CalendarEventType | None = None,
    tag_id: int | None = None,
    date_from: dt.datetime | None = None,
    date_to: dt.datetime | None = None,
    q: str | None = None,
) -> list[CalendarEventRead]:
    stmt = select(CalendarEvent)
    if project_id is not None:
        stmt = stmt.where(CalendarEvent.project_id == project_id)
    if all_teams_only:
        stmt = stmt.where(CalendarEvent.all_teams.is_(True))
    elif team_id is not None:
        stmt = stmt.where(CalendarEvent.team_id == team_id)
    if owner_user_id is not None:
        stmt = stmt.where(CalendarEvent.owner_user_id == owner_user_id)
    if event_type is not None:
        stmt = stmt.where(CalendarEvent.event_type == event_type)
    if tag_id is not None:
        stmt = stmt.where(
            CalendarEvent.id.in_(
                select(TagAssociation.entity_id).where(
                    TagAssociation.entity_type == TaggableType.CALENDAR_EVENT,
                    TagAssociation.tag_id == tag_id,
                )
            )
        )
    if date_from is not None:
        stmt = stmt.where(CalendarEvent.end_datetime >= date_from)
    if date_to is not None:
        stmt = stmt.where(CalendarEvent.start_datetime <= date_to)
    if q:
        stmt = stmt.where(CalendarEvent.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(CalendarEvent.start_datetime)
    events = db.scalars(stmt).all()
    return [_serialize(db, e) for e in events]


def get_calendar_event(db: Session, event_id: int) -> CalendarEventRead:
    event = db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return _serialize(db, event)


def create_calendar_event(
    db: Session, payload: CalendarEventCreate
) -> CalendarEventRead:
    ensure_project_editable(db, payload.project_id)
    _validate_dates(payload.start_datetime, payload.end_datetime)
    _validate_team_scope(payload.all_teams, payload.team_id)
    if payload.team_id is not None:
        _get_team_or_404(db, payload.team_id)
    if payload.owner_user_id is not None:
        _get_user_or_404(db, payload.owner_user_id)
    if payload.related_activity_id is not None:
        _get_activity_or_404(db, payload.related_activity_id)
    if (payload.recurrence_frequency is None) != (payload.recurrence_end_date is None):
        raise HTTPException(
            status_code=422,
            detail="recurrence_frequency and recurrence_end_date must be set together.",
        )
    if (
        payload.recurrence_end_date is not None
        and payload.recurrence_end_date < payload.start_datetime.date()
    ):
        raise HTTPException(
            status_code=422,
            detail="recurrence_end_date must not be before the event's start date.",
        )

    data = payload.model_dump()
    tag_ids = data.pop("tag_ids")
    recurrence_frequency = data.pop("recurrence_frequency")
    recurrence_end_date = data.pop("recurrence_end_date")

    if recurrence_frequency is None:
        event = CalendarEvent(**data)
        db.add(event)
        db.flush()
        _sync_tags(db, event, tag_ids)
        db.commit()
        db.refresh(event)
        return _serialize(db, event)

    duration = data["end_datetime"] - data["start_datetime"]
    occurrence_starts = _generate_occurrence_starts(
        data["start_datetime"], recurrence_frequency, recurrence_end_date
    )

    occurrences = []
    for occurrence_start in occurrence_starts:
        occurrence = CalendarEvent(
            **{
                **data,
                "start_datetime": occurrence_start,
                "end_datetime": occurrence_start + duration,
                "recurrence_frequency": recurrence_frequency,
                "recurrence_end_date": recurrence_end_date,
            }
        )
        db.add(occurrence)
        occurrences.append(occurrence)
    db.flush()  # assigns ids, needed for recurrence_group_id below

    leader = occurrences[0]
    for occurrence in occurrences:
        occurrence.recurrence_group_id = leader.id
        _sync_tags(db, occurrence, tag_ids)

    db.commit()
    db.refresh(leader)
    return _serialize(db, leader)


def update_calendar_event(
    db: Session, event_id: int, payload: CalendarEventUpdate
) -> CalendarEventRead:
    event = db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    ensure_project_editable(db, event.project_id)

    data = payload.model_dump(exclude_unset=True)
    new_start = data.get("start_datetime", event.start_datetime)
    new_end = data.get("end_datetime", event.end_datetime)
    _validate_dates(new_start, new_end)
    _validate_team_scope(
        data.get("all_teams", event.all_teams), data.get("team_id", event.team_id)
    )

    if data.get("team_id") is not None:
        _get_team_or_404(db, data["team_id"])
    if data.get("owner_user_id") is not None:
        _get_user_or_404(db, data["owner_user_id"])
    if data.get("related_activity_id") is not None:
        _get_activity_or_404(db, data["related_activity_id"])

    tag_ids = data.pop("tag_ids", None)
    for field, value in data.items():
        setattr(event, field, value)
    if tag_ids is not None:
        _sync_tags(db, event, tag_ids)

    db.commit()
    db.refresh(event)
    return _serialize(db, event)


def delete_calendar_event(db: Session, event_id: int, delete_future: bool = False) -> None:
    """`delete_future=True` deletes this occurrence and every later one in
    its recurrence series (never earlier ones — those already happened).
    Safe as a single bulk delete: occurrences are generated forward in time
    from the series leader, so the leader always has the earliest
    start_datetime in its group — meaning this can never delete a row while
    leaving another row's recurrence_group_id dangling (pointing at a
    leader this call just removed) without also removing that row."""
    event = db.get(CalendarEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    ensure_project_editable(db, event.project_id)
    if delete_future and event.recurrence_group_id is not None:
        db.query(CalendarEvent).filter(
            CalendarEvent.recurrence_group_id == event.recurrence_group_id,
            CalendarEvent.start_datetime >= event.start_datetime,
        ).delete(synchronize_session=False)
    else:
        db.delete(event)
    db.commit()
