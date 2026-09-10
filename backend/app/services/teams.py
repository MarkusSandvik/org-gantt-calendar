import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team, TeamMembership
from app.schemas.team import TeamCreate, TeamMemberRead, TeamUpdate, TeamWithMembersRead
from app.services.projects import ensure_project_editable


def _serialize(db: Session, team: Team) -> TeamWithMembersRead:
    memberships = db.scalars(
        select(TeamMembership).where(TeamMembership.team_id == team.id)
    ).all()
    members = sorted(
        (
            TeamMemberRead(
                id=m.user.id, name=m.user.name, email=m.user.email, team_role=m.team_role
            )
            for m in memberships
        ),
        key=lambda m: (m.team_role.value != "lead", m.name),
    )
    return TeamWithMembersRead(
        id=team.id,
        project_id=team.project_id,
        name=team.name,
        category=team.category,
        color=team.color,
        sort_order=team.sort_order,
        auto_transfer_membership=team.auto_transfer_membership,
        members=members,
    )


def list_teams(db: Session, project_id: int | None) -> list[TeamWithMembersRead]:
    stmt = select(Team).where(Team.archived_at.is_(None))
    if project_id is not None:
        stmt = stmt.where(Team.project_id == project_id)
    stmt = stmt.order_by(Team.sort_order)
    return [_serialize(db, t) for t in db.scalars(stmt).all()]


def _get_team_or_404(db: Session, team_id: int) -> Team:
    team = db.get(Team, team_id)
    if team is None or team.archived_at is not None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def create_team(db: Session, payload: TeamCreate) -> TeamWithMembersRead:
    ensure_project_editable(db, payload.project_id)
    next_sort_order = (
        db.scalar(select(Team.sort_order).order_by(Team.sort_order.desc()).limit(1)) or 0
    ) + 1
    team = Team(
        project_id=payload.project_id,
        name=payload.name,
        category=payload.category,
        color=payload.color,
        sort_order=next_sort_order,
        auto_transfer_membership=payload.auto_transfer_membership,
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return _serialize(db, team)


def update_team(db: Session, team_id: int, payload: TeamUpdate) -> TeamWithMembersRead:
    team = _get_team_or_404(db, team_id)
    ensure_project_editable(db, team.project_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return _serialize(db, team)


def delete_team(db: Session, team_id: int) -> None:
    team = _get_team_or_404(db, team_id)
    ensure_project_editable(db, team.project_id)
    team.archived_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    db.commit()
