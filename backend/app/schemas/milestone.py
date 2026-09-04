import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MilestoneStatus


class MilestoneTeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MilestoneUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class MilestoneTagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str | None


class MilestoneBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    date: dt.date
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    team_id: int | None = None
    owner_user_id: int | None = None


class MilestoneCreate(MilestoneBase):
    project_id: int
    tag_ids: list[int] = Field(default_factory=list)


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    date: dt.date | None = None
    status: MilestoneStatus | None = None
    team_id: int | None = None
    owner_user_id: int | None = None
    tag_ids: list[int] | None = None


class MilestoneRead(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None
    date: dt.date
    status: MilestoneStatus
    team: MilestoneTeamRead | None
    owner_user: MilestoneUserRead | None
    tags: list[MilestoneTagRead]
