import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core import permissions
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import CommentableType, MilestoneStatus
from app.models.milestone import Milestone
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.milestone import MilestoneCreate, MilestoneRead, MilestoneUpdate
from app.services import comments as comment_service
from app.services import milestones as milestone_service

router = APIRouter(prefix="/milestones", tags=["milestones"])


def _get_milestone_or_404(db: Session, milestone_id: int) -> Milestone:
    milestone = db.get(Milestone, milestone_id)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.get("", response_model=list[MilestoneRead])
def list_milestones(
    project_id: int | None = None,
    team_id: int | None = None,
    owner_user_id: int | None = None,
    status: MilestoneStatus | None = None,
    tag_id: int | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MilestoneRead]:
    return milestone_service.list_milestones(
        db,
        project_id=project_id,
        team_id=team_id,
        owner_user_id=owner_user_id,
        status=status,
        tag_id=tag_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )


@router.get("/{milestone_id}", response_model=MilestoneRead)
def get_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneRead:
    return milestone_service.get_milestone(db, milestone_id)


@router.post("", response_model=MilestoneRead, status_code=201)
def create_milestone(
    payload: MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneRead:
    permissions.require(
        permissions.can_manage_milestone_for_team(db, current_user, payload.team_id)
    )
    return milestone_service.create_milestone(db, payload)


@router.patch("/{milestone_id}", response_model=MilestoneRead)
def update_milestone(
    milestone_id: int,
    payload: MilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MilestoneRead:
    milestone = _get_milestone_or_404(db, milestone_id)
    permissions.require(permissions.can_manage_milestone(db, current_user, milestone))
    return milestone_service.update_milestone(
        db, milestone_id, payload, user_id=current_user.id
    )


@router.delete("/{milestone_id}", status_code=204)
def delete_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    milestone = _get_milestone_or_404(db, milestone_id)
    permissions.require(permissions.can_manage_milestone(db, current_user, milestone))
    milestone_service.delete_milestone(db, milestone_id)
    return Response(status_code=204)


@router.get("/{milestone_id}/comments", response_model=list[CommentRead])
def list_milestone_comments(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CommentRead]:
    milestone_service.get_milestone(db, milestone_id)  # 404 if missing
    return comment_service.list_comments(db, CommentableType.MILESTONE, milestone_id)


@router.post("/{milestone_id}/comments", response_model=CommentRead, status_code=201)
def create_milestone_comment(
    milestone_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentRead:
    milestone = _get_milestone_or_404(db, milestone_id)
    permissions.require(permissions.can_comment_on_milestone(db, current_user, milestone))
    return comment_service.create_comment(
        db, CommentableType.MILESTONE, milestone_id, payload, author_id=current_user.id
    )
