from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core import permissions
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.dependency import Dependency
from app.models.user import User
from app.schemas.dependency import DependencyCreate, DependencyRead
from app.services import dependencies as dependency_service

router = APIRouter(prefix="/dependencies", tags=["dependencies"])


def _get_dependency_or_404(db: Session, dependency_id: int) -> Dependency:
    dependency = db.get(Dependency, dependency_id)
    if dependency is None:
        raise HTTPException(status_code=404, detail="Dependency not found")
    return dependency


@router.get("", response_model=list[DependencyRead])
def list_dependencies(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[DependencyRead]:
    return dependency_service.list_dependencies(db)


@router.post("", response_model=DependencyRead, status_code=201)
def create_dependency(
    payload: DependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DependencyRead:
    permissions.require(
        permissions.can_manage_dependency(
            db,
            current_user,
            payload.predecessor_type,
            payload.predecessor_id,
            payload.successor_type,
            payload.successor_id,
        )
    )
    return dependency_service.create_dependency(db, payload)


@router.delete("/{dependency_id}", status_code=204)
def delete_dependency(
    dependency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    dependency = _get_dependency_or_404(db, dependency_id)
    permissions.require(
        permissions.can_manage_dependency(
            db,
            current_user,
            dependency.predecessor_type,
            dependency.predecessor_id,
            dependency.successor_type,
            dependency.successor_id,
        )
    )
    dependency_service.delete_dependency(db, dependency_id)
    return Response(status_code=204)
