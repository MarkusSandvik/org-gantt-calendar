import datetime as dt

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import utc_now
from app.db.base import Base


class PasswordResetToken(Base):
    """Single-use, time-limited password reset token. As with invitations
    and sessions, only the token's hash is persisted."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(default=utc_now)
    expires_at: Mapped[dt.datetime] = mapped_column()
    used_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    user: Mapped["User"] = relationship()  # noqa: F821
