from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ActivityStatus, Priority
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityRead, ActivityUpdate
from app.services import activities as activity_service

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list[ActivityRead])
def list_activities(
    project_id: int | None = None,
    team_id: int | None = None,
    owner_user_id: int | None = None,
    status: ActivityStatus | None = None,
    priority: Priority | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[ActivityRead]:
    return activity_service.list_activities(
        db,
        project_id=project_id,
        team_id=team_id,
        owner_user_id=owner_user_id,
        status=status,
        priority=priority,
        q=q,
    )


@router.get("/{activity_id}", response_model=ActivityRead)
def get_activity(activity_id: int, db: Session = Depends(get_db)) -> ActivityRead:
    return activity_service.get_activity(db, activity_id)


@router.post("", response_model=ActivityRead, status_code=201)
def create_activity(
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityRead:
    return activity_service.create_activity(db, payload, created_by_id=current_user.id)


@router.patch("/{activity_id}", response_model=ActivityRead)
def update_activity(
    activity_id: int, payload: ActivityUpdate, db: Session = Depends(get_db)
) -> ActivityRead:
    return activity_service.update_activity(db, activity_id, payload)


@router.delete("/{activity_id}", status_code=204)
def delete_activity(activity_id: int, db: Session = Depends(get_db)) -> Response:
    activity_service.delete_activity(db, activity_id)
    return Response(status_code=204)
