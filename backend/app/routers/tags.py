from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import permissions
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services import tags as tag_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Tag]:
    return tag_service.list_tags(db, project_id)


@router.post("", response_model=TagRead, status_code=201)
def create_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tag:
    permissions.require(permissions.can_manage_tag(current_user))
    return tag_service.create_tag(db, payload)


@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tag:
    permissions.require(permissions.can_manage_tag(current_user))
    return tag_service.update_tag(db, tag_id, payload)


@router.delete("/{tag_id}", status_code=204)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    permissions.require(permissions.can_manage_tag(current_user))
    tag_service.delete_tag(db, tag_id)
