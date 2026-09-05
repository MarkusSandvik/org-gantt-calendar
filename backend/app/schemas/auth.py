import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GlobalRole, TeamRole, UserStatus


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1)


class MeTeamMembership(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: int
    team_name: str
    team_role: TeamRole


class MeRead(BaseModel):
    id: int
    name: str
    email: str
    global_role: GlobalRole
    status: UserStatus
    last_login_at: dt.datetime | None
    team_memberships: list[MeTeamMembership]


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=200)
