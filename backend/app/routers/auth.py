from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.auth_cookies import clear_auth_cookies, set_auth_cookies
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeRead,
    PasswordResetConfirm,
    PasswordResetRequest,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=MeRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> MeRead:
    client_ip = request.client.host if request.client else "unknown"
    user = auth_service.authenticate(
        db, payload.email, payload.password, rate_limit_key=f"{client_ip}:{payload.email}"
    )
    session_token = auth_service.create_session(db, user, request.headers.get("user-agent"))
    set_auth_cookies(response, session_token)
    return auth_service.serialize_me(db, user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
    db: Session = Depends(get_db),
) -> Response:
    if session_token:
        auth_service.revoke_session(db, session_token)
    clear_auth_cookies(response)
    return Response(status_code=204)


@router.get("/me", response_model=MeRead)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeRead:
    return auth_service.serialize_me(db, current_user)


@router.post("/password-reset/request", status_code=204)
def request_password_reset(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> Response:
    # Always returns 204 regardless of whether the email exists — the
    # dev-mode raw token/URL is logged server-side only (see
    # services/auth.py), never reflected in this response, so the HTTP
    # behavior can't be used to enumerate accounts.
    token = auth_service.request_password_reset(db, payload.email)
    if token is not None and settings.environment == "local":
        print(f"[dev] Password reset link for {payload.email}: /reset-password?token={token}")
    return Response(status_code=204)


@router.post("/password-reset/confirm", status_code=204)
def confirm_password_reset(
    payload: PasswordResetConfirm, db: Session = Depends(get_db)
) -> Response:
    auth_service.confirm_password_reset(db, payload.token, payload.new_password)
    return Response(status_code=204)
