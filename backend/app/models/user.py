import datetime as dt

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import GlobalRole, UserStatus


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(300))
    global_role: Mapped[GlobalRole] = mapped_column(Enum(GlobalRole), default=GlobalRole.USER)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.PENDING)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    team_memberships: Mapped[list["TeamMembership"]] = relationship(  # noqa: F821
        back_populates="user"
    )
