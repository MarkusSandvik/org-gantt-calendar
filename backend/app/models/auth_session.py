import datetime as dt

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import utc_now
from app.db.base import Base


class AuthSession(Base):
    """A server-side login session. The cookie sent to the browser holds
    the raw token; only its SHA-256 hash is stored here, so a database
    leak alone can't be used to hijack a session. Revoking (logout,
    deactivating a user) is a single row update — the reason sessions
    are used instead of stateless JWTs for this single-service API."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)
    expires_at: Mapped[dt.datetime] = mapped_column()
    revoked_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    user_agent: Mapped[str | None] = mapped_column(String(400))

    user: Mapped["User"] = relationship()  # noqa: F821
