import datetime as dt

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import MilestoneStatus
from app.schemas.milestone import MilestoneCreate, MilestoneRead, MilestoneUpdate
from app.services import milestones as milestone_service

router = APIRouter(prefix="/milestones", tags=["milestones"])


@router.get("", response_model=list[MilestoneRead])
def list_milestones(
    project_id: int | None = None,
    team_id: int | None = None,
    status: MilestoneStatus | None = None,
    tag_id: int | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[MilestoneRead]:
    return milestone_service.list_milestones(
        db,
        project_id=project_id,
        team_id=team_id,
        status=status,
        tag_id=tag_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )


@router.get("/{milestone_id}", response_model=MilestoneRead)
def get_milestone(milestone_id: int, db: Session = Depends(get_db)) -> MilestoneRead:
    return milestone_service.get_milestone(db, milestone_id)


@router.post("", response_model=MilestoneRead, status_code=201)
def create_milestone(
    payload: MilestoneCreate, db: Session = Depends(get_db)
) -> MilestoneRead:
    return milestone_service.create_milestone(db, payload)


@router.patch("/{milestone_id}", response_model=MilestoneRead)
def update_milestone(
    milestone_id: int, payload: MilestoneUpdate, db: Session = Depends(get_db)
) -> MilestoneRead:
    return milestone_service.update_milestone(db, milestone_id, payload)


@router.delete("/{milestone_id}", status_code=204)
def delete_milestone(milestone_id: int, db: Session = Depends(get_db)) -> Response:
    milestone_service.delete_milestone(db, milestone_id)
    return Response(status_code=204)
