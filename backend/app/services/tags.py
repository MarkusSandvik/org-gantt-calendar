import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate
from app.services.projects import ensure_project_editable


def list_tags(db: Session, project_id: int | None) -> list[Tag]:
    stmt = select(Tag).where(Tag.archived_at.is_(None))
    if project_id is not None:
        stmt = stmt.where(Tag.project_id == project_id)
    stmt = stmt.order_by(Tag.name)
    return list(db.scalars(stmt).all())


def _get_tag_or_404(db: Session, tag_id: int) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None or tag.archived_at is not None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


def create_tag(db: Session, payload: TagCreate) -> Tag:
    ensure_project_editable(db, payload.project_id)
    tag = Tag(project_id=payload.project_id, name=payload.name, color=payload.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: int, payload: TagUpdate) -> Tag:
    tag = _get_tag_or_404(db, tag_id)
    ensure_project_editable(db, tag.project_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(tag, field, value)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> None:
    tag = _get_tag_or_404(db, tag_id)
    ensure_project_editable(db, tag.project_id)
    tag.archived_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    db.commit()
