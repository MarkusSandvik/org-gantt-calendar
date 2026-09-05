import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import permissions
from app.core.config import get_settings
from app.core.security import generate_token, hash_password, hash_token, utc_now
from app.models.enums import GlobalRole, InvitationStatus, TeamRole, UserStatus
from app.models.invitation import Invitation
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.auth import MeRead
from app.schemas.invitation import (
    InvitationAccept,
    InvitationCreate,
    InvitationCreateResponse,
    InvitationPreview,
    InvitationRead,
)
from app.services import audit_log as audit_log_service
from app.services import auth as auth_service

_settings = get_settings()


def _serialize(invitation: Invitation) -> InvitationRead:
    return InvitationRead.model_validate(invitation)


def _authorize_invitation_scope(db: Session, actor: User, payload: InvitationCreate) -> None:
    """Derives what the actor is allowed to invite from who THEY are —
    never from the request payload. A Lead's request is checked against
    their own team and MEMBER-only target role; nothing in the payload
    can widen that, no matter what it claims (Section 9/16)."""
    if permissions.is_admin(actor):
        if payload.target_global_role == GlobalRole.ADMIN:
            if payload.team_id is not None or payload.target_team_role is not None:
                raise HTTPException(
                    status_code=422,
                    detail="An Admin invitation cannot also carry a team assignment.",
                )
        else:
            if payload.team_id is None or payload.target_team_role is None:
                raise HTTPException(
                    status_code=422,
                    detail="A Member/Lead invitation requires both team_id and target_team_role.",
                )
            if db.get(Team, payload.team_id) is None:
                raise HTTPException(status_code=404, detail="Team not found")
        return

    led_team_id = permissions.get_led_team_id(db, actor)
    if led_team_id is None:
        raise HTTPException(
            status_code=403, detail="Only a team Lead or Admin can invite users."
        )
    if (
        payload.target_global_role != GlobalRole.USER
        or payload.target_team_role != TeamRole.MEMBER
        or payload.team_id != led_team_id
    ):
        raise HTTPException(
            status_code=403,
            detail="A Lead may only invite Members into their own team.",
        )


def create_invitation(
    db: Session, actor: User, payload: InvitationCreate
) -> InvitationCreateResponse:
    _authorize_invitation_scope(db, actor, payload)

    existing_user = db.scalars(select(User).where(User.email == payload.email)).first()
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="A user with that email already exists")

    token = generate_token()
    invitation = Invitation(
        email=payload.email,
        name=payload.name,
        team_id=payload.team_id,
        target_global_role=payload.target_global_role,
        target_team_role=payload.target_team_role,
        invited_by_user_id=actor.id,
        token_hash=hash_token(token),
        status=InvitationStatus.PENDING,
        expires_at=utc_now() + dt.timedelta(hours=_settings.invitation_ttl_hours),
    )
    db.add(invitation)
    db.flush()

    audit_log_service.write_field_changes(
        db,
        "invitation",
        invitation.id,
        actor.id,
        [("email", None, payload.email), ("status", None, InvitationStatus.PENDING.value)],
        f"Invited as {payload.target_global_role.value}"
        + (f"/{payload.target_team_role.value}" if payload.target_team_role else ""),
    )
    db.commit()
    db.refresh(invitation)

    response = InvitationCreateResponse.model_validate(invitation)
    if _settings.environment == "local":
        response.invite_url = f"/accept-invitation?token={token}"
    return response


def list_invitations(db: Session, actor: User, team_id: int | None = None) -> list[InvitationRead]:
    stmt = select(Invitation)
    if permissions.is_admin(actor):
        if team_id is not None:
            stmt = stmt.where(Invitation.team_id == team_id)
    else:
        led_team_id = permissions.get_led_team_id(db, actor)
        if led_team_id is None:
            raise HTTPException(
                status_code=403, detail="Only a team Lead or Admin can view invitations."
            )
        stmt = stmt.where(Invitation.team_id == led_team_id)
    stmt = stmt.order_by(Invitation.created_at.desc())
    return [_serialize(i) for i in db.scalars(stmt).all()]


def revoke_invitation(db: Session, actor: User, invitation_id: int) -> None:
    invitation = db.get(Invitation, invitation_id)
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if not permissions.is_admin(actor):
        led_team_id = permissions.get_led_team_id(db, actor)
        if led_team_id is None or invitation.team_id != led_team_id:
            raise HTTPException(
                status_code=403, detail="You can only revoke invitations for your own team."
            )

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only a pending invitation can be revoked")

    old_status = invitation.status
    invitation.status = InvitationStatus.REVOKED
    audit_log_service.write_field_changes(
        db,
        "invitation",
        invitation.id,
        actor.id,
        [("status", old_status.value, InvitationStatus.REVOKED.value)],
        None,
    )
    db.commit()


def preview_invitation(db: Session, token: str) -> InvitationPreview:
    invitation = _get_valid_pending_invitation(db, token)
    team = db.get(Team, invitation.team_id) if invitation.team_id else None
    return InvitationPreview(
        email=invitation.email,
        name=invitation.name,
        team_name=team.name if team else None,
        target_global_role=invitation.target_global_role,
        target_team_role=invitation.target_team_role,
    )


def _get_valid_pending_invitation(db: Session, token: str) -> Invitation:
    invitation = db.scalars(
        select(Invitation).where(Invitation.token_hash == hash_token(token))
    ).first()
    if invitation is None or invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    if invitation.expires_at < utc_now():
        invitation.status = InvitationStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    return invitation


def accept_invitation(db: Session, payload: InvitationAccept) -> tuple[MeRead, str]:
    """Creates the account, marks the invitation accepted, and returns a
    fresh session token alongside the new user — so accepting an
    invitation logs the user straight in rather than requiring a second
    separate login."""
    invitation = _get_valid_pending_invitation(db, payload.token)

    user = User(
        name=invitation.name,
        email=invitation.email,
        password_hash=hash_password(payload.password),
        global_role=invitation.target_global_role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()

    if invitation.team_id is not None and invitation.target_team_role is not None:
        db.add(
            TeamMembership(
                team_id=invitation.team_id, user_id=user.id, team_role=invitation.target_team_role
            )
        )

    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = utc_now()

    audit_log_service.write_field_changes(
        db, "user", user.id, user.id, [("status", None, UserStatus.ACTIVE.value)], "Invitation accepted"
    )
    db.commit()
    db.refresh(user)

    session_token = auth_service.create_session(db, user, user_agent=None)
    return auth_service.serialize_me(db, user), session_token
