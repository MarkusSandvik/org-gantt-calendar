from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dependency import DependencyCreate, DependencyRead
from app.services import dependencies as dependency_service

router = APIRouter(prefix="/dependencies", tags=["dependencies"])


@router.get("", response_model=list[DependencyRead])
def list_dependencies(db: Session = Depends(get_db)) -> list[DependencyRead]:
    return dependency_service.list_dependencies(db)


@router.post("", response_model=DependencyRead, status_code=201)
def create_dependency(
    payload: DependencyCreate, db: Session = Depends(get_db)
) -> DependencyRead:
    return dependency_service.create_dependency(db, payload)


@router.delete("/{dependency_id}", status_code=204)
def delete_dependency(dependency_id: int, db: Session = Depends(get_db)) -> Response:
    dependency_service.delete_dependency(db, dependency_id)
    return Response(status_code=204)
