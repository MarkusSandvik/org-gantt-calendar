from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.enums import CommentableType
from app.schemas.comment import CommentAuthorRead, CommentCreate, CommentRead


def _serialize(comment: Comment) -> CommentRead:
    return CommentRead(
        id=comment.id,
        author=CommentAuthorRead.model_validate(comment.author),
        body=comment.body,
        created_at=comment.created_at,
        status_change_from=comment.status_change_from,
        status_change_to=comment.status_change_to,
    )


def list_comments(
    db: Session, entity_type: CommentableType, entity_id: int
) -> list[CommentRead]:
    comments = db.scalars(
        select(Comment)
        .where(Comment.entity_type == entity_type, Comment.entity_id == entity_id)
        .order_by(Comment.created_at)
    ).all()
    return [_serialize(c) for c in comments]


def create_comment(
    db: Session,
    entity_type: CommentableType,
    entity_id: int,
    payload: CommentCreate,
    author_id: int,
) -> CommentRead:
    comment = Comment(
        entity_type=entity_type, entity_id=entity_id, author_id=author_id, body=payload.body
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _serialize(comment)


def create_status_change_comment(
    db: Session,
    entity_type: CommentableType,
    entity_id: int,
    author_id: int,
    old_status: str,
    new_status: str,
    note: str | None,
) -> None:
    """Records a status transition as its own log entry — per the master
    spec, status changes belong in the chronological activity log, not
    folded into the generic field-change audit trail."""
    db.add(
        Comment(
            entity_type=entity_type,
            entity_id=entity_id,
            author_id=author_id,
            body=note or "",
            status_change_from=old_status,
            status_change_to=new_status,
        )
    )
