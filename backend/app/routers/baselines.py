from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import permissions
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.baseline import BaselineComparison, BaselineCreate, BaselineRead
from app.services import baselines as baseline_service

router = APIRouter(prefix="/baselines", tags=["baselines"])


@router.get("", response_model=list[BaselineRead])
def list_baselines(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BaselineRead]:
    return baseline_service.list_baselines(db, project_id)


@router.post("", response_model=BaselineRead, status_code=201)
def create_baseline(
    project_id: int,
    payload: BaselineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BaselineRead:
    permissions.require(permissions.can_manage_baseline(current_user))
    return baseline_service.create_baseline(db, project_id, payload, user_id=current_user.id)


@router.get("/{baseline_id}/comparison", response_model=BaselineComparison)
def get_baseline_comparison(
    baseline_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BaselineComparison:
    return baseline_service.get_baseline_comparison(db, baseline_id)
