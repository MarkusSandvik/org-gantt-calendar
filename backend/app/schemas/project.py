import datetime as dt

from pydantic import BaseModel, ConfigDict


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    start_date: dt.date | None
    end_date: dt.date | None
    auto_scheduling_enabled: bool
