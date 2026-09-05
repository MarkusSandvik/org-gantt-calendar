import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core import permissions
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.activity import Activity
from app.models.enums import ActivityStatus, CommentableType, Priority
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityRead, ActivityUpdate
from app.schemas.comment import CommentCreate, CommentRead
from app.services import activities as activity_service
from app.services import comments as comment_service

router = APIRouter(prefix="/activities", tags=["activities"])


def _get_activity_or_404(db: Session, activity_id: int) -> Activity:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.get("", response_model=list[ActivityRead])
def list_activities(
    project_id: int | None = None,
    team_id: int | None = None,
    owner_user_id: int | None = None,
    contributor_user_id: int | None = None,
    tag_id: int | None = None,
    status: ActivityStatus | None = None,
    priority: Priority | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ActivityRead]:
    return activity_service.list_activities(
        db,
        project_id=project_id,
        team_id=team_id,
        owner_user_id=owner_user_id,
        contributor_user_id=contributor_user_id,
        tag_id=tag_id,
        status=status,
        priority=priority,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )


@router.get("/{activity_id}", response_model=ActivityRead)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityRead:
    return activity_service.get_activity(db, activity_id)


@router.post("", response_model=ActivityRead, status_code=201)
def create_activity(
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityRead:
    permissions.require(
        permissions.can_create_activity(db, current_user, payload.owner_team_id)
    )
    return activity_service.create_activity(db, payload, created_by_id=current_user.id)


@router.patch("/{activity_id}", response_model=ActivityRead)
def update_activity(
    activity_id: int,
    payload: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityRead:
    activity = _get_activity_or_404(db, activity_id)
    data = payload.model_dump(exclude_unset=True)
    data.pop("reason", None)
    changed_fields = permissions.compute_changed_activity_fields(db, activity, data)
    permissions.require(
        permissions.can_update_activity_fields(db, current_user, activity, changed_fields)
    )
    return activity_service.update_activity(db, activity_id, payload, user_id=current_user.id)


@router.delete("/{activity_id}", status_code=204)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    activity = _get_activity_or_404(db, activity_id)
    permissions.require(permissions.can_delete_activity(db, current_user, activity))
    activity_service.delete_activity(db, activity_id)
    return Response(status_code=204)


@router.get("/{activity_id}/comments", response_model=list[CommentRead])
def list_activity_comments(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CommentRead]:
    activity_service.get_activity(db, activity_id)  # 404 if missing
    return comment_service.list_comments(db, CommentableType.ACTIVITY, activity_id)


@router.post("/{activity_id}/comments", response_model=CommentRead, status_code=201)
def create_activity_comment(
    activity_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentRead:
    activity = _get_activity_or_404(db, activity_id)
    permissions.require(permissions.can_comment_on_activity(db, current_user, activity))
    return comment_service.create_comment(
        db, CommentableType.ACTIVITY, activity_id, payload, author_id=current_user.id
    )
