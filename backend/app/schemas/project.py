import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProjectStatus


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    season_label: str | None
    description: str | None
    start_date: dt.date | None
    end_date: dt.date | None
    status: ProjectStatus
    is_default: bool
    auto_scheduling_enabled: bool
    archived_at: dt.datetime | None
    created_by_id: int | None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=100)
    season_label: str | None = Field(default=None, max_length=50)
    description: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    # When set, the new project's Teams and Tags are duplicated from this
    # source project (structure only — no activities, milestones, events,
    # or team memberships carry over; see Section 11 of the design doc).
    copy_structure_from_project_id: int | None = None


class ProjectUpdate(BaseModel):
    # Deliberately no `slug` field — the slug is baked into every bookmarked
    # /:projectSlug/... URL, so changing it after creation would break links
    # rather than just relabeling the project. Rename the project's display
    # name instead.
    name: str | None = Field(default=None, min_length=1, max_length=200)
    season_label: str | None = Field(default=None, max_length=50)
    description: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus
