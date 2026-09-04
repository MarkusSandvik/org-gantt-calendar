import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.models.enums import MilestoneStatus


class MilestoneTeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MilestoneUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    date: dt.date
    status: MilestoneStatus
    team: MilestoneTeamRead | None
    owner_user: MilestoneUserRead | None
