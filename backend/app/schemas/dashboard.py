import datetime as dt

from pydantic import BaseModel

from app.models.enums import ActivityStatus


class WeekCounts(BaseModel):
    active_tasks: int
    milestones_this_week: int
    delayed: int
    blocked: int
    social_activities: int
    meetings: int
    upcoming_deadlines: int


class UpcomingMilestone(BaseModel):
    id: int
    title: str
    date: dt.date
    team: str | None


class AttentionItem(BaseModel):
    id: int
    title: str
    status: ActivityStatus
    detail: str


class DashboardSummary(BaseModel):
    iso_year: int
    iso_week: int
    week_start: dt.date
    week_end: dt.date
    week_counts: WeekCounts
    upcoming_milestones: list[UpcomingMilestone]
    attention_required: list[AttentionItem]
