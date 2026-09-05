from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import UserStatus
from app.models.user import User
from app.schemas.user import (
    GlobalRoleUpdate,
    TeamMembershipSet,
    UserAdminRead,
    UserRead,
)
from app.services import user_admin as user_admin_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[User]:
    return list(
        db.scalars(
            select(User).where(User.status == UserStatus.ACTIVE).order_by(User.name)
        ).all()
    )


@router.get("/admin", response_model=list[UserAdminRead])
def list_users_for_admin(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[UserAdminRead]:
    return user_admin_service.list_users_for_admin(db, current_user)


@router.post("/{user_id}/deactivate", response_model=UserAdminRead)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAdminRead:
    return user_admin_service.set_user_status(db, current_user, user_id, UserStatus.INACTIVE)


@router.post("/{user_id}/reactivate", response_model=UserAdminRead)
def reactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAdminRead:
    return user_admin_service.set_user_status(db, current_user, user_id, UserStatus.ACTIVE)


@router.put("/{user_id}/team-memberships", response_model=UserAdminRead)
def set_team_membership(
    user_id: int,
    payload: TeamMembershipSet,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAdminRead:
    return user_admin_service.set_team_membership(db, current_user, user_id, payload)


@router.delete("/{user_id}/team-memberships/{team_id}", status_code=204)
def remove_team_membership(
    user_id: int,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    user_admin_service.remove_team_membership(db, current_user, user_id, team_id)


@router.patch("/{user_id}/global-role", response_model=UserAdminRead)
def set_global_role(
    user_id: int,
    payload: GlobalRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAdminRead:
    return user_admin_service.set_global_role(db, current_user, user_id, payload.global_role)
