import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GlobalRole, InvitationStatus, TeamRole


class InvitationCreate(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    name: str = Field(min_length=1, max_length=200)
    team_id: int | None = None
    target_global_role: GlobalRole
    target_team_role: TeamRole | None = None


class InvitationTeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class InvitationInviterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    team: InvitationTeamRead | None
    target_global_role: GlobalRole
    target_team_role: TeamRole | None
    invited_by: InvitationInviterRead
    status: InvitationStatus
    expires_at: dt.datetime
    created_at: dt.datetime
    accepted_at: dt.datetime | None


class InvitationCreateResponse(InvitationRead):
    # Populated only in local development (see Settings.environment) — the
    # dev-friendly stand-in for actually emailing the invite, per the
    # master plan's Section 8. Never populated outside local dev.
    invite_url: str | None = None


class InvitationPreview(BaseModel):
    """What an unauthenticated invitee sees before setting a password —
    deliberately minimal, no ids or internal details."""

    email: str
    name: str
    team_name: str | None
    target_global_role: GlobalRole
    target_team_role: TeamRole | None


class InvitationAccept(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=200)
