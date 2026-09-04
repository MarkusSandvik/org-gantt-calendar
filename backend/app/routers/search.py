from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.search import SearchResult
from app.services import search as search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
def search(
    q: str, project_id: int | None = None, db: Session = Depends(get_db)
) -> list[SearchResult]:
    return search_service.global_search(db, q, project_id=project_id)
