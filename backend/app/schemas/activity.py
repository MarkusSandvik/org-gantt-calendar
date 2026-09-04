import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActivityStatus, Priority


class ActivityTeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ActivityUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ActivityTagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str | None


class ActivityBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    start_date: dt.date
    end_date: dt.date
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    progress_percent: int = Field(default=0, ge=0, le=100)
    priority: Priority = Priority.NORMAL
    owner_team_id: int | None = None
    owner_user_id: int | None = None


class ActivityCreate(ActivityBase):
    project_id: int
    contributor_user_ids: list[int] = Field(default_factory=list)
    tag_ids: list[int] = Field(default_factory=list)


class ActivityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    status: ActivityStatus | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    priority: Priority | None = None
    owner_team_id: int | None = None
    owner_user_id: int | None = None
    contributor_user_ids: list[int] | None = None
    tag_ids: list[int] | None = None
    reason: str | None = Field(default=None, max_length=1000)


class ActivityRead(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None
    start_date: dt.date
    end_date: dt.date
    status: ActivityStatus
    progress_percent: int
    priority: Priority
    owner_team: ActivityTeamRead | None
    owner_user: ActivityUserRead | None
    created_by: ActivityUserRead | None
    contributors: list[ActivityUserRead]
    tags: list[ActivityTagRead]
    created_at: dt.datetime
    updated_at: dt.datetime
