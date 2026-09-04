import datetime as dt

from pydantic import BaseModel, ConfigDict


class AuditLogUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AuditLogRead(BaseModel):
    id: int
    user: AuditLogUserRead
    timestamp: dt.datetime
    field_name: str
    old_value: str | None
    new_value: str | None
    reason: str | None
    change_group_id: str | None
