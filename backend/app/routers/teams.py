from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.team import Team
from app.schemas.team import TeamRead

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamRead])
def list_teams(
    project_id: int | None = None, db: Session = Depends(get_db)
) -> list[Team]:
    stmt = select(Team).where(Team.archived_at.is_(None))
    if project_id is not None:
        stmt = stmt.where(Team.project_id == project_id)
    stmt = stmt.order_by(Team.sort_order)
    return list(db.scalars(stmt).all())
