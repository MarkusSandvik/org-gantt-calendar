from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.services import auth as auth_service

_settings = get_settings()


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=_settings.session_cookie_name),
    db: Session = Depends(get_db),
) -> User:
    """Resolves the logged-in user from the HttpOnly session cookie. Every
    router that previously depended on this (for attribution, and now for
    authorization too) keeps working unchanged — only this function's
    internals moved from the mocked X-User-Id header to a real session."""
    if session_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = auth_service.get_user_for_session_token(db, session_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
