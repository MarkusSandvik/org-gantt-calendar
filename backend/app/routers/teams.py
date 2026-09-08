from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import permissions
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate, TeamWithMembersRead
from app.services import teams as team_service

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamWithMembersRead])
def list_teams(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TeamWithMembersRead]:
    return team_service.list_teams(db, project_id)


@router.post("", response_model=TeamWithMembersRead, status_code=201)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamWithMembersRead:
    permissions.require(permissions.can_manage_team(current_user))
    return team_service.create_team(db, payload)


@router.patch("/{team_id}", response_model=TeamWithMembersRead)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamWithMembersRead:
    permissions.require(permissions.can_manage_team(current_user))
    return team_service.update_team(db, team_id, payload)


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    permissions.require(permissions.can_manage_team(current_user))
    team_service.delete_team(db, team_id)
