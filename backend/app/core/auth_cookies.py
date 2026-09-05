from fastapi import Response

from app.core.config import get_settings
from app.core.security import generate_token

settings = get_settings()


def set_auth_cookies(response: Response, session_token: str) -> None:
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    # Non-HttpOnly by design: the frontend reads this to echo it back as
    # an X-CSRF-Token header on mutating requests (double-submit check).
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=generate_token(),
        max_age=max_age,
        httponly=False,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
