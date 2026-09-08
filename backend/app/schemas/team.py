from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TeamCategory, TeamRole


class TeamMemberRead(BaseModel):
    id: int
    name: str
    email: str
    team_role: TeamRole


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    category: TeamCategory
    color: str | None
    sort_order: int


class TeamWithMembersRead(TeamRead):
    members: list[TeamMemberRead]


class TeamCreate(BaseModel):
    project_id: int
    name: str = Field(min_length=1, max_length=200)
    category: TeamCategory
    color: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: TeamCategory | None = None
    color: str | None = None
