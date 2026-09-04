from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.audit_log import AuditLogRead
from app.services import audit_log as audit_log_service

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_log(
    entity_type: str, entity_id: int, db: Session = Depends(get_db)
) -> list[AuditLogRead]:
    return audit_log_service.list_audit_log(db, entity_type, entity_id)
