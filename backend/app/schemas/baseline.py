import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BaselineCreatorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BaselineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    note: str | None = None


class BaselineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    note: str | None
    created_by: BaselineCreatorRead
    created_at: dt.datetime


class BaselineDriftItem(BaseModel):
    entity_type: Literal["activity", "milestone"]
    entity_id: int
    label: str
    baseline_start: dt.date
    baseline_end: dt.date
    current_start: dt.date
    current_end: dt.date
    delta_start_days: int
    delta_end_days: int


class BaselineComparison(BaseModel):
    baseline: BaselineRead
    items: list[BaselineDriftItem]
