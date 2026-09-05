import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import InMemorySlidingWindowRateLimiter
from app.core.security import (
    generate_token,
    hash_password,
    hash_token,
    utc_now,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.enums import UserStatus
from app.models.password_reset_token import PasswordResetToken
from app.models.team import TeamMembership
from app.models.user import User
from app.schemas.auth import MeRead, MeTeamMembership
from app.services import audit_log as audit_log_service

GENERIC_LOGIN_ERROR = "Invalid email or password"

_settings = get_settings()
login_rate_limiter = InMemorySlidingWindowRateLimiter(
    max_attempts=_settings.login_rate_limit_attempts,
    window_seconds=_settings.login_rate_limit_window_seconds,
)


def authenticate(db: Session, email: str, password: str, rate_limit_key: str) -> User:
    """Verifies credentials and returns the User, or raises a 401 with a
    generic message — the same message and (as close as practical) the
    same code path for 'unknown email' and 'wrong password', so a caller
    can't use response differences to enumerate valid accounts."""
    if not login_rate_limiter.hit(rate_limit_key):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again shortly.")

    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None or user.password_hash is None:
        # Run a hash verification anyway so the response time doesn't
        # leak whether the email exists.
        verify_password(password, hash_password("decoy-password"))
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=401, detail=GENERIC_LOGIN_ERROR)

    return user


def create_session(db: Session, user: User, user_agent: str | None) -> str:
    """Creates a new server-side session and returns the raw token — the
    caller sets this as the HttpOnly cookie value. Only its hash is
    persisted."""
    token = generate_token()
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=utc_now() + dt.timedelta(hours=_settings.session_ttl_hours),
        user_agent=user_agent[:400] if user_agent else None,
    )
    db.add(session)
    user.last_login_at = utc_now()
    db.commit()
    return token


def get_user_for_session_token(db: Session, token: str) -> User | None:
    token_hash = hash_token(token)
    session = db.scalars(
        select(AuthSession).where(AuthSession.token_hash == token_hash)
    ).first()
    if session is None or session.revoked_at is not None:
        return None
    if session.expires_at < utc_now():
        return None
    user = db.get(User, session.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        return None
    return user


def revoke_session(db: Session, token: str) -> None:
    token_hash = hash_token(token)
    session = db.scalars(
        select(AuthSession).where(AuthSession.token_hash == token_hash)
    ).first()
    if session is not None and session.revoked_at is None:
        session.revoked_at = utc_now()
        db.commit()


def serialize_me(db: Session, user: User) -> MeRead:
    memberships = db.scalars(
        select(TeamMembership).where(TeamMembership.user_id == user.id)
    ).all()
    return MeRead(
        id=user.id,
        name=user.name,
        email=user.email,
        global_role=user.global_role,
        status=user.status,
        last_login_at=user.last_login_at,
        team_memberships=[
            MeTeamMembership(
                team_id=m.team_id, team_name=m.team.name, team_role=m.team_role
            )
            for m in memberships
        ],
    )


def request_password_reset(db: Session, email: str) -> str | None:
    """Returns the raw reset token for a known, active user, or None for
    an unknown email — the router always responds the same way either
    way, so this return value is for the dev-mode 'show the link' UI
    only, never reflected in the HTTP response body."""
    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None or user.status != UserStatus.ACTIVE:
        return None

    token = generate_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=utc_now()
            + dt.timedelta(hours=_settings.password_reset_ttl_hours),
        )
    )
    db.commit()
    return token


def confirm_password_reset(db: Session, token: str, new_password: str) -> None:
    token_hash = hash_token(token)
    reset = db.scalars(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).first()
    if reset is None or reset.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if reset.expires_at < utc_now():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.get(User, reset.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = hash_password(new_password)
    reset.used_at = utc_now()

    # Revoke every existing session for this user — a password reset
    # should end any session started with the old, possibly-compromised
    # password, not just apply going forward.
    for session in db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)
        )
    ):
        session.revoked_at = utc_now()

    audit_log_service.write_field_changes(
        db, "user", user.id, user.id, [("password", "***", "***")], "Password reset completed"
    )
    db.commit()
