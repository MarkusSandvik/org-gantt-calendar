from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User


def get_current_user(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    """Mocked-auth current user. The frontend sends the "acting as" user's id
    via X-User-Id; if omitted (e.g. direct API calls), fall back to the
    first user so the API stays usable without a header. A real login can
    replace this dependency later without changing any call sites."""
    if x_user_id is not None:
        user = db.get(User, x_user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Unknown X-User-Id")
        return user

    user = db.scalars(select(User).order_by(User.id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="No users exist yet")
    return user
