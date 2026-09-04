import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.models.enums import CalendarEventType


class CalendarEventTeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CalendarEventUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CalendarEventActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str


class CalendarEventBase(BaseModel):
    title: str
    description: str | None = None
    event_type: CalendarEventType
    start_datetime: dt.datetime
    end_datetime: dt.datetime
    all_day: bool = False
    location: str | None = None
    team_id: int | None = None
    owner_user_id: int | None = None
    related_activity_id: int | None = None


class CalendarEventCreate(CalendarEventBase):
    project_id: int


class CalendarEventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    event_type: CalendarEventType | None = None
    start_datetime: dt.datetime | None = None
    end_datetime: dt.datetime | None = None
    all_day: bool | None = None
    location: str | None = None
    team_id: int | None = None
    owner_user_id: int | None = None
    related_activity_id: int | None = None


class CalendarEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    description: str | None
    event_type: CalendarEventType
    start_datetime: dt.datetime
    end_datetime: dt.datetime
    all_day: bool
    location: str | None
    team: CalendarEventTeamRead | None
    owner_user: CalendarEventUserRead | None
    related_activity: CalendarEventActivityRead | None
    created_at: dt.datetime
    updated_at: dt.datetime
