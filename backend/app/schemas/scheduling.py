import datetime as dt

from pydantic import BaseModel

from app.models.enums import SchedulableType


class SchedulingChangeRequest(BaseModel):
    entity_type: SchedulableType
    entity_id: int
    new_start_date: dt.date
    new_end_date: dt.date
    reason: str | None = None


class ScheduleChangeItem(BaseModel):
    entity_type: SchedulableType
    entity_id: int
    label: str
    old_start_date: dt.date
    old_end_date: dt.date
    new_start_date: dt.date
    new_end_date: dt.date
    delta_days: int


class SchedulingApplyResponse(BaseModel):
    change_group_id: str
    changes: list[ScheduleChangeItem]


class SchedulingUndoRequest(BaseModel):
    change_group_id: str
