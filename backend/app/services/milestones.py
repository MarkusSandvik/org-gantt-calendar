import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dependency import Dependency
from app.models.enums import CommentableType, MilestoneStatus, SchedulableType, TaggableType
from app.models.milestone import Milestone
from app.models.tag import Tag, TagAssociation
from app.models.team import Team
from app.models.user import User
from app.schemas.milestone import (
    MilestoneCreate,
    MilestoneRead,
    MilestoneTagRead,
    MilestoneTeamRead,
    MilestoneUpdate,
    MilestoneUserRead,
)
from app.services import audit_log as audit_log_service
from app.services import comments as comment_service

AUDITED_MILESTONE_FIELDS = ("title", "description", "date", "team_id", "owner_user_id")


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


def _sync_tags(db: Session, milestone: Milestone, tag_ids: list[int]) -> None:
    _get_tags_or_404(db, tag_ids)
    db.query(TagAssociation).filter(
        TagAssociation.entity_type == TaggableType.MILESTONE,
        TagAssociation.entity_id == milestone.id,
    ).delete()
    for tid in tag_ids:
        db.add(
            TagAssociation(
                tag_id=tid, entity_type=TaggableType.MILESTONE, entity_id=milestone.id
            )
        )


def _serialize(db: Session, milestone: Milestone) -> MilestoneRead:
    tag_rows = db.scalars(
        select(Tag)
        .join(TagAssociation, TagAssociation.tag_id == Tag.id)
        .where(
            TagAssociation.entity_type == TaggableType.MILESTONE,
            TagAssociation.entity_id == milestone.id,
        )
        .order_by(Tag.name)
    ).all()
    return MilestoneRead(
        id=milestone.id,
        project_id=milestone.project_id,
        title=milestone.title,
        description=milestone.description,
        date=milestone.date,
        status=milestone.status,
        team=MilestoneTeamRead.model_validate(milestone.team) if milestone.team else None,
        owner_user=MilestoneUserRead.model_validate(milestone.owner_user)
        if milestone.owner_user
        else None,
        tags=[MilestoneTagRead.model_validate(t) for t in tag_rows],
    )


def list_milestones(
    db: Session,
    project_id: int | None = None,
    team_id: int | None = None,
    owner_user_id: int | None = None,
    status: MilestoneStatus | None = None,
    tag_id: int | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    q: str | None = None,
) -> list[MilestoneRead]:
    stmt = select(Milestone)
    if project_id is not None:
        stmt = stmt.where(Milestone.project_id == project_id)
    if team_id is not None:
        stmt = stmt.where(Milestone.team_id == team_id)
    if owner_user_id is not None:
        stmt = stmt.where(Milestone.owner_user_id == owner_user_id)
    if status is not None:
        stmt = stmt.where(Milestone.status == status)
    if date_from is not None:
        stmt = stmt.where(Milestone.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Milestone.date <= date_to)
    if tag_id is not None:
        stmt = stmt.where(
            Milestone.id.in_(
                select(TagAssociation.entity_id).where(
                    TagAssociation.entity_type == TaggableType.MILESTONE,
                    TagAssociation.tag_id == tag_id,
                )
            )
        )
    if q:
        stmt = stmt.where(Milestone.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Milestone.date)
    milestones = db.scalars(stmt).all()
    return [_serialize(db, m) for m in milestones]


def get_milestone(db: Session, milestone_id: int) -> MilestoneRead:
    milestone = db.get(Milestone, milestone_id)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return _serialize(db, milestone)


def create_milestone(db: Session, payload: MilestoneCreate) -> MilestoneRead:
    if payload.team_id is not None:
        _get_team_or_404(db, payload.team_id)
    if payload.owner_user_id is not None:
        _get_user_or_404(db, payload.owner_user_id)

    milestone = Milestone(
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        date=payload.date,
        status=payload.status,
        team_id=payload.team_id,
        owner_user_id=payload.owner_user_id,
    )
    db.add(milestone)
    db.flush()

    _sync_tags(db, milestone, payload.tag_ids)

    db.commit()
    db.refresh(milestone)
    return _serialize(db, milestone)


def update_milestone(
    db: Session, milestone_id: int, payload: MilestoneUpdate, user_id: int
) -> MilestoneRead:
    milestone = db.get(Milestone, milestone_id)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    data = payload.model_dump(exclude_unset=True)
    reason = data.pop("reason", None)

    if data.get("team_id") is not None:
        _get_team_or_404(db, data["team_id"])
    if data.get("owner_user_id") is not None:
        _get_user_or_404(db, data["owner_user_id"])

    tag_ids = data.pop("tag_ids", None)
    new_status = data.pop("status", None)
    old_status = milestone.status

    field_changes = [
        (field, getattr(milestone, field), data[field])
        for field in AUDITED_MILESTONE_FIELDS
        if field in data and getattr(milestone, field) != data[field]
    ]

    for field, value in data.items():
        setattr(milestone, field, value)
    if new_status is not None:
        milestone.status = new_status

    if tag_ids is not None:
        _sync_tags(db, milestone, tag_ids)

    if field_changes:
        audit_log_service.write_field_changes(
            db, "milestone", milestone.id, user_id, field_changes, reason
        )
    if new_status is not None and new_status != old_status:
        comment_service.create_status_change_comment(
            db,
            CommentableType.MILESTONE,
            milestone.id,
            user_id,
            old_status.value,
            new_status.value,
            reason,
        )

    db.commit()
    db.refresh(milestone)
    return _serialize(db, milestone)


def delete_milestone(db: Session, milestone_id: int) -> None:
    milestone = db.get(Milestone, milestone_id)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    blocking = db.scalars(
        select(Dependency).where(
            (
                (Dependency.predecessor_type == SchedulableType.MILESTONE)
                & (Dependency.predecessor_id == milestone_id)
            )
            | (
                (Dependency.successor_type == SchedulableType.MILESTONE)
                & (Dependency.successor_id == milestone_id)
            )
        )
    ).first()
    if blocking is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a milestone that has dependencies. Remove the dependency first.",
        )

    db.query(TagAssociation).filter(
        TagAssociation.entity_type == TaggableType.MILESTONE,
        TagAssociation.entity_id == milestone_id,
    ).delete()
    db.delete(milestone)
    db.commit()
