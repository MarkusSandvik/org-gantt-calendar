import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GlobalRole, TeamRole, UserStatus


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    global_role: GlobalRole
    status: UserStatus
    last_login_at: dt.datetime | None


class UserAdminTeamMembership(BaseModel):
    team_id: int
    team_name: str
    team_role: TeamRole


class UserAdminRead(BaseModel):
    id: int
    name: str
    email: str
    global_role: GlobalRole
    status: UserStatus
    last_login_at: dt.datetime | None
    created_at: dt.datetime
    team_memberships: list[UserAdminTeamMembership]


class TeamMembershipSet(BaseModel):
    team_id: int
    team_role: TeamRole


class GlobalRoleUpdate(BaseModel):
    global_role: GlobalRole = Field(description="The user's new organization-wide role")
