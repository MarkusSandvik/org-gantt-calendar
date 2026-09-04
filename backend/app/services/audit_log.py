import enum
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogRead, AuditLogUserRead


def to_audit_string(value: object) -> str | None:
    """Stringify a field value for audit storage. Explicit `.value` for
    Enums rather than relying on str() — Python's Enum.__str__ formatting
    for `(str, Enum)` mixins is version-dependent and not something to
    lean on for a stored audit trail."""
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        return value.value
    return str(value)


def write_field_changes(
    db: Session,
    entity_type: str,
    entity_id: int,
    user_id: int,
    changes: list[tuple[str, object, object]],
    reason: str | None,
) -> None:
    """Writes one AuditLog row per (field_name, old_value, new_value) triple,
    all sharing a single change_group_id — the same grouping convention the
    scheduling engine uses, so a set of edits saved together reads as one
    event in the log rather than several unrelated-looking rows."""
    if not changes:
        return
    change_group_id = uuid.uuid4().hex
    for field_name, old_value, new_value in changes:
        db.add(
            AuditLog(
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                field_name=field_name,
                old_value=to_audit_string(old_value),
                new_value=to_audit_string(new_value),
                reason=reason,
                change_group_id=change_group_id,
            )
        )


def list_audit_log(db: Session, entity_type: str, entity_id: int) -> list[AuditLogRead]:
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        .order_by(AuditLog.timestamp)
    ).all()
    return [
        AuditLogRead(
            id=log.id,
            user=AuditLogUserRead.model_validate(log.user),
            timestamp=log.timestamp,
            field_name=log.field_name,
            old_value=log.old_value,
            new_value=log.new_value,
            reason=log.reason,
            change_group_id=log.change_group_id,
        )
        for log in logs
    ]
