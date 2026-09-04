from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.milestone import Milestone
from app.schemas.milestone import MilestoneRead

router = APIRouter(prefix="/milestones", tags=["milestones"])


@router.get("", response_model=list[MilestoneRead])
def list_milestones(
    project_id: int | None = None, db: Session = Depends(get_db)
) -> list[Milestone]:
    stmt = select(Milestone)
    if project_id is not None:
        stmt = stmt.where(Milestone.project_id == project_id)
    stmt = stmt.order_by(Milestone.date)
    return list(db.scalars(stmt).all())
