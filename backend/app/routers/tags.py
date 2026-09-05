from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Tag]:
    stmt = select(Tag).where(Tag.archived_at.is_(None))
    if project_id is not None:
        stmt = stmt.where(Tag.project_id == project_id)
    stmt = stmt.order_by(Tag.name)
    return list(db.scalars(stmt).all())
