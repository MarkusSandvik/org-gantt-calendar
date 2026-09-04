import datetime as dt

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.db.base import Base


class AuditLog(Base):
    """Generic field-level change record for any entity type. Rows sharing a
    change_group_id came from a single scheduling cascade and can be undone together."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    timestamp: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC)
    )
    field_name: Mapped[str] = mapped_column(String(100))
    old_value: Mapped[str | None] = mapped_column(String(2000))
    new_value: Mapped[str | None] = mapped_column(String(2000))
    reason: Mapped[str | None] = mapped_column(String(1000))
    change_group_id: Mapped[str | None] = mapped_column(String(64))

    user: Mapped["User"] = relationship()  # noqa: F821
