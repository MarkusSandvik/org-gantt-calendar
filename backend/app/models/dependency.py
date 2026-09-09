from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import DependencyType, SchedulableType


class Dependency(TimestampMixin, Base):
    """Edge in the scheduling graph. Endpoints are polymorphic (activity or milestone)
    so both kinds of schedulable object can depend on each other."""

    __tablename__ = "dependencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Denormalized from the endpoints (both must already belong to the same
    # project — enforced in services/dependencies.py) so the scheduling
    # engine and list endpoints can filter edges by project directly,
    # without resolving each polymorphic endpoint just to find its project.
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    predecessor_type: Mapped[SchedulableType] = mapped_column(Enum(SchedulableType))
    predecessor_id: Mapped[int] = mapped_column(Integer)
    successor_type: Mapped[SchedulableType] = mapped_column(Enum(SchedulableType))
    successor_id: Mapped[int] = mapped_column(Integer)
    dependency_type: Mapped[DependencyType] = mapped_column(
        Enum(DependencyType), default=DependencyType.FINISH_TO_START
    )
    lag_days: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped["Project"] = relationship(back_populates="dependencies")  # noqa: F821
