from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import permissions
from app.models.enums import GlobalRole, TeamRole, UserStatus
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.user import TeamMembershipSet, UserAdminRead, UserAdminTeamMembership
from app.services import audit_log as audit_log_service


def _serialize(db: Session, user: User) -> UserAdminRead:
    memberships = db.scalars(
        select(TeamMembership).where(TeamMembership.user_id == user.id)
    ).all()
    return UserAdminRead(
        id=user.id,
        name=user.name,
        email=user.email,
        global_role=user.global_role,
        status=user.status,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        team_memberships=[
            UserAdminTeamMembership(
                team_id=m.team_id, team_name=m.team.name, team_role=m.team_role
            )
            for m in memberships
        ],
    )


def list_users_for_admin(db: Session, actor: User) -> list[UserAdminRead]:
    if permissions.is_admin(actor):
        users = db.scalars(select(User).order_by(User.name)).all()
    else:
        led_team_id = permissions.get_led_team_id(db, actor)
        if led_team_id is None:
            raise HTTPException(
                status_code=403, detail="Only a team Lead or Admin can view user administration."
            )
        member_ids = db.scalars(
            select(TeamMembership.user_id).where(
                TeamMembership.team_id == led_team_id, TeamMembership.team_role == TeamRole.MEMBER
            )
        ).all()
        users = db.scalars(
            select(User).where(User.id.in_(member_ids)).order_by(User.name)
        ).all()
    return [_serialize(db, u) for u in users]


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def set_user_status(
    db: Session, actor: User, target_user_id: int, new_status: UserStatus
) -> UserAdminRead:
    if actor.id == target_user_id:
        raise HTTPException(status_code=400, detail="You cannot change your own account status")

    target = _get_user_or_404(db, target_user_id)
    permissions.require(permissions.can_deactivate_user(db, actor, target))

    old_status = target.status
    target.status = new_status
    audit_log_service.write_field_changes(
        db, "user", target.id, actor.id, [("status", old_status.value, new_status.value)], None
    )
    db.commit()
    db.refresh(target)
    return _serialize(db, target)


def set_team_membership(
    db: Session, actor: User, target_user_id: int, payload: TeamMembershipSet
) -> UserAdminRead:
    permissions.require(permissions.can_manage_team(actor))

    target = _get_user_or_404(db, target_user_id)
    if db.get(Team, payload.team_id) is None:
        raise HTTPException(status_code=404, detail="Team not found")

    if payload.team_role == TeamRole.LEAD:
        # A user leads at most one team — demote any existing Lead
        # membership elsewhere before granting this one (see RBAC_PLAN.md).
        for existing in db.scalars(
            select(TeamMembership).where(
                TeamMembership.user_id == target.id,
                TeamMembership.team_role == TeamRole.LEAD,
                TeamMembership.team_id != payload.team_id,
            )
        ):
            existing.team_role = TeamRole.MEMBER
            audit_log_service.write_field_changes(
                db,
                "team_membership",
                existing.id,
                actor.id,
                [("team_role", "lead", "member")],
                "Reassigned as Lead of a different team",
            )

    existing_here = db.scalars(
        select(TeamMembership).where(
            TeamMembership.user_id == target.id, TeamMembership.team_id == payload.team_id
        )
    ).first()
    if existing_here is None:
        membership = TeamMembership(
            team_id=payload.team_id, user_id=target.id, team_role=payload.team_role
        )
        db.add(membership)
        audit_log_service.write_field_changes(
            db,
            "user",
            target.id,
            actor.id,
            [("team_membership_added", None, f"{payload.team_id}:{payload.team_role.value}")],
            None,
        )
    else:
        old_role = existing_here.team_role
        existing_here.team_role = payload.team_role
        audit_log_service.write_field_changes(
            db,
            "team_membership",
            existing_here.id,
            actor.id,
            [("team_role", old_role.value, payload.team_role.value)],
            None,
        )

    db.commit()
    db.refresh(target)
    return _serialize(db, target)


def remove_team_membership(db: Session, actor: User, target_user_id: int, team_id: int) -> None:
    permissions.require(permissions.can_manage_team(actor))

    membership = db.scalars(
        select(TeamMembership).where(
            TeamMembership.user_id == target_user_id, TeamMembership.team_id == team_id
        )
    ).first()
    if membership is None:
        raise HTTPException(status_code=404, detail="Team membership not found")

    audit_log_service.write_field_changes(
        db,
        "user",
        target_user_id,
        actor.id,
        [("team_membership_removed", f"{team_id}:{membership.team_role.value}", None)],
        None,
    )
    db.delete(membership)
    db.commit()


def set_global_role(
    db: Session, actor: User, target_user_id: int, new_role: GlobalRole
) -> UserAdminRead:
    permissions.require(permissions.is_admin(actor))
    if actor.id == target_user_id:
        raise HTTPException(status_code=400, detail="You cannot change your own global role")

    target = _get_user_or_404(db, target_user_id)
    old_role = target.global_role
    target.global_role = new_role
    audit_log_service.write_field_changes(
        db, "user", target.id, actor.id, [("global_role", old_role.value, new_role.value)], None
    )
    db.commit()
    db.refresh(target)
    return _serialize(db, target)
