import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity, ActivityContributor
from app.models.dependency import Dependency
from app.models.enums import (
    ActivityStatus,
    CommentableType,
    Priority,
    SchedulableType,
    TaggableType,
)
from app.models.tag import Tag, TagAssociation
from app.models.team import Team
from app.models.user import User
from app.schemas.activity import (
    ActivityCreate,
    ActivityRead,
    ActivityTagRead,
    ActivityTeamRead,
    ActivityUpdate,
    ActivityUserRead,
)
from app.services import audit_log as audit_log_service
from app.services import comments as comment_service

AUDITED_ACTIVITY_FIELDS = (
    "title",
    "description",
    "start_date",
    "end_date",
    "progress_percent",
    "priority",
    "owner_team_id",
    "owner_user_id",
)


def _validate_dates(start_date: dt.date, end_date: dt.date) -> None:
    if end_date < start_date:
        raise HTTPException(
            status_code=422, detail="end_date must not be before start_date"
        )


def _get_team_or_404(db: Session, team_id: int) -> None:
    if db.get(Team, team_id) is None:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")


def _get_user_or_404(db: Session, user_id: int) -> None:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")


def _get_tags_or_404(db: Session, tag_ids: list[int]) -> None:
    if not tag_ids:
        return
    found_ids = set(db.scalars(select(Tag.id).where(Tag.id.in_(tag_ids))).all())
    missing = set(tag_ids) - found_ids
    if missing:
        raise HTTPException(status_code=404, detail=f"Tag(s) not found: {sorted(missing)}")


def _sync_contributors(db: Session, activity: Activity, user_ids: list[int]) -> None:
    for uid in user_ids:
        _get_user_or_404(db, uid)
    db.query(ActivityContributor).filter(
        ActivityContributor.activity_id == activity.id
    ).delete()
    for uid in user_ids:
        db.add(ActivityContributor(activity_id=activity.id, user_id=uid))


def _sync_tags(db: Session, activity: Activity, tag_ids: list[int]) -> None:
    _get_tags_or_404(db, tag_ids)
    db.query(TagAssociation).filter(
        TagAssociation.entity_type == TaggableType.ACTIVITY,
        TagAssociation.entity_id == activity.id,
    ).delete()
    for tid in tag_ids:
        db.add(
            TagAssociation(
                tag_id=tid, entity_type=TaggableType.ACTIVITY, entity_id=activity.id
            )
        )


def _serialize(db: Session, activity: Activity) -> ActivityRead:
    contributor_rows = db.scalars(
        select(User)
        .join(ActivityContributor, ActivityContributor.user_id == User.id)
        .where(ActivityContributor.activity_id == activity.id)
        .order_by(User.name)
    ).all()
    tag_rows = db.scalars(
        select(Tag)
        .join(TagAssociation, TagAssociation.tag_id == Tag.id)
        .where(
            TagAssociation.entity_type == TaggableType.ACTIVITY,
            TagAssociation.entity_id == activity.id,
        )
        .order_by(Tag.name)
    ).all()
    return ActivityRead(
        id=activity.id,
        project_id=activity.project_id,
        title=activity.title,
        description=activity.description,
        start_date=activity.start_date,
        end_date=activity.end_date,
        status=activity.status,
        progress_percent=activity.progress_percent,
        priority=activity.priority,
        owner_team=ActivityTeamRead.model_validate(activity.owner_team)
        if activity.owner_team
        else None,
        owner_user=ActivityUserRead.model_validate(activity.owner_user)
        if activity.owner_user
        else None,
        created_by=ActivityUserRead.model_validate(activity.created_by)
        if activity.created_by
        else None,
        contributors=[ActivityUserRead.model_validate(u) for u in contributor_rows],
        tags=[ActivityTagRead.model_validate(t) for t in tag_rows],
        created_at=activity.created_at,
        updated_at=activity.updated_at,
    )


def list_activities(
    db: Session,
    project_id: int | None = None,
    team_id: int | None = None,
    owner_user_id: int | None = None,
    contributor_user_id: int | None = None,
    tag_id: int | None = None,
    status: ActivityStatus | None = None,
    priority: Priority | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    q: str | None = None,
) -> list[ActivityRead]:
    stmt = select(Activity)
    if project_id is not None:
        stmt = stmt.where(Activity.project_id == project_id)
    if team_id is not None:
        stmt = stmt.where(Activity.owner_team_id == team_id)
    if owner_user_id is not None:
        stmt = stmt.where(Activity.owner_user_id == owner_user_id)
    if contributor_user_id is not None:
        stmt = stmt.where(
            Activity.id.in_(
                select(ActivityContributor.activity_id).where(
                    ActivityContributor.user_id == contributor_user_id
                )
            )
        )
    if tag_id is not None:
        stmt = stmt.where(
            Activity.id.in_(
                select(TagAssociation.entity_id).where(
                    TagAssociation.entity_type == TaggableType.ACTIVITY,
                    TagAssociation.tag_id == tag_id,
                )
            )
        )
    if status is not None:
        stmt = stmt.where(Activity.status == status)
    if priority is not None:
        stmt = stmt.where(Activity.priority == priority)
    if date_from is not None:
        stmt = stmt.where(Activity.end_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Activity.start_date <= date_to)
    if q:
        stmt = stmt.where(Activity.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Activity.start_date)
    activities = db.scalars(stmt).all()
    return [_serialize(db, a) for a in activities]


def get_activity(db: Session, activity_id: int) -> ActivityRead:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return _serialize(db, activity)


def create_activity(
    db: Session, payload: ActivityCreate, created_by_id: int
) -> ActivityRead:
    _validate_dates(payload.start_date, payload.end_date)
    if payload.owner_team_id is not None:
        _get_team_or_404(db, payload.owner_team_id)
    if payload.owner_user_id is not None:
        _get_user_or_404(db, payload.owner_user_id)

    activity = Activity(
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        progress_percent=payload.progress_percent,
        priority=payload.priority,
        owner_team_id=payload.owner_team_id,
        owner_user_id=payload.owner_user_id,
        created_by_id=created_by_id,
    )
    db.add(activity)
    db.flush()

    _sync_contributors(db, activity, payload.contributor_user_ids)
    _sync_tags(db, activity, payload.tag_ids)

    db.commit()
    db.refresh(activity)
    return _serialize(db, activity)


def update_activity(
    db: Session, activity_id: int, payload: ActivityUpdate, user_id: int
) -> ActivityRead:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    data = payload.model_dump(exclude_unset=True)
    reason = data.pop("reason", None)

    new_start = data.get("start_date", activity.start_date)
    new_end = data.get("end_date", activity.end_date)
    _validate_dates(new_start, new_end)

    if data.get("owner_team_id") is not None:
        _get_team_or_404(db, data["owner_team_id"])
    if data.get("owner_user_id") is not None:
        _get_user_or_404(db, data["owner_user_id"])

    contributor_ids = data.pop("contributor_user_ids", None)
    tag_ids = data.pop("tag_ids", None)
    new_status = data.pop("status", None)
    old_status = activity.status

    # Status changes are recorded as their own chronological log entry
    # (a Comment with status_change_from/to), not folded into the generic
    # field-change audit trail — see the master spec's Comments section.
    field_changes = [
        (field, getattr(activity, field), data[field])
        for field in AUDITED_ACTIVITY_FIELDS
        if field in data and getattr(activity, field) != data[field]
    ]

    for field, value in data.items():
        setattr(activity, field, value)
    if new_status is not None:
        activity.status = new_status

    if contributor_ids is not None:
        _sync_contributors(db, activity, contributor_ids)
    if tag_ids is not None:
        _sync_tags(db, activity, tag_ids)

    if field_changes:
        audit_log_service.write_field_changes(
            db, "activity", activity.id, user_id, field_changes, reason
        )
    if new_status is not None and new_status != old_status:
        comment_service.create_status_change_comment(
            db,
            CommentableType.ACTIVITY,
            activity.id,
            user_id,
            old_status.value,
            new_status.value,
            reason,
        )

    db.commit()
    db.refresh(activity)
    return _serialize(db, activity)


def delete_activity(db: Session, activity_id: int) -> None:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    blocking = db.scalars(
        select(Dependency).where(
            (
                (Dependency.predecessor_type == SchedulableType.ACTIVITY)
                & (Dependency.predecessor_id == activity_id)
            )
            | (
                (Dependency.successor_type == SchedulableType.ACTIVITY)
                & (Dependency.successor_id == activity_id)
            )
        )
    ).first()
    if blocking is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete an activity that has dependencies. Remove the dependency first.",
        )

    db.query(ActivityContributor).filter(
        ActivityContributor.activity_id == activity_id
    ).delete()
    db.query(TagAssociation).filter(
        TagAssociation.entity_type == TaggableType.ACTIVITY,
        TagAssociation.entity_id == activity_id,
    ).delete()
    db.delete(activity)
    db.commit()
