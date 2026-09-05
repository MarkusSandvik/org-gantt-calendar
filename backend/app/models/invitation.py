import datetime as dt

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import GlobalRole, InvitationStatus, TeamRole


class Invitation(TimestampMixin, Base):
    """A pending account-creation offer. Only a hash of the invitation
    token is stored — see app/core/security.py — so a leaked database
    dump can't be used to accept invitations directly."""

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str] = mapped_column(String(200))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    target_global_role: Mapped[GlobalRole] = mapped_column(Enum(GlobalRole))
    target_team_role: Mapped[TeamRole | None] = mapped_column(Enum(TeamRole))
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus), default=InvitationStatus.PENDING
    )
    expires_at: Mapped[dt.datetime] = mapped_column()
    accepted_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    team: Mapped["Team | None"] = relationship()  # noqa: F821
    invited_by: Mapped["User"] = relationship()  # noqa: F821
