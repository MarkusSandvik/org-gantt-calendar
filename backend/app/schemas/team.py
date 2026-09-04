from pydantic import BaseModel, ConfigDict

from app.models.enums import TeamCategory


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    category: TeamCategory
    color: str | None
    sort_order: int
