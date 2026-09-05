from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.auth_cookies import set_auth_cookies
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MeRead
from app.schemas.invitation import (
    InvitationAccept,
    InvitationCreate,
    InvitationCreateResponse,
    InvitationPreview,
    InvitationRead,
)
from app.services import invitations as invitation_service

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("", response_model=InvitationCreateResponse, status_code=201)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvitationCreateResponse:
    return invitation_service.create_invitation(db, current_user, payload)


@router.get("", response_model=list[InvitationRead])
def list_invitations(
    team_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvitationRead]:
    return invitation_service.list_invitations(db, current_user, team_id=team_id)


@router.post("/{invitation_id}/revoke", status_code=204)
def revoke_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    invitation_service.revoke_invitation(db, current_user, invitation_id)
    return Response(status_code=204)


@router.get("/preview/{token}", response_model=InvitationPreview)
def preview_invitation(token: str, db: Session = Depends(get_db)) -> InvitationPreview:
    return invitation_service.preview_invitation(db, token)


@router.post("/accept", response_model=MeRead)
def accept_invitation(
    payload: InvitationAccept, response: Response, db: Session = Depends(get_db)
) -> MeRead:
    me, session_token = invitation_service.accept_invitation(db, payload)
    set_auth_cookies(response, session_token)
    return me
