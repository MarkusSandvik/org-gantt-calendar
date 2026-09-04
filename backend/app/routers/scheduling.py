from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.scheduling import (
    ScheduleChangeItem,
    SchedulingApplyResponse,
    SchedulingChangeRequest,
    SchedulingUndoRequest,
)
from app.services import scheduling as scheduling_service

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


@router.post("/preview", response_model=list[ScheduleChangeItem])
def preview(
    payload: SchedulingChangeRequest, db: Session = Depends(get_db)
) -> list[ScheduleChangeItem]:
    return scheduling_service.preview_schedule_change(db, payload)


@router.post("/apply", response_model=SchedulingApplyResponse)
def apply_change(
    payload: SchedulingChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SchedulingApplyResponse:
    return scheduling_service.apply_schedule_change(db, payload, user_id=current_user.id)


@router.post("/undo", response_model=list[ScheduleChangeItem])
def undo(
    payload: SchedulingUndoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScheduleChangeItem]:
    return scheduling_service.undo_schedule_change(
        db, payload.change_group_id, user_id=current_user.id
    )
