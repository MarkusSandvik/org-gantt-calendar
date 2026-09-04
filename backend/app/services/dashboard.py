import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.calendar_event import CalendarEvent
from app.models.dependency import Dependency
from app.models.enums import (
    ActivityStatus,
    CalendarEventType,
    MilestoneStatus,
    SchedulableType,
)
from app.models.milestone import Milestone
from app.schemas.dashboard import (
    AttentionItem,
    DashboardSummary,
    UpcomingMilestone,
    WeekCounts,
)

UPCOMING_MILESTONES_LIMIT = 5


def _week_bounds(today: dt.date) -> tuple[dt.date, dt.date]:
    monday = today - dt.timedelta(days=today.weekday())
    sunday = monday + dt.timedelta(days=6)
    return monday, sunday


def _count(db: Session, stmt) -> int:
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def _blocked_detail(db: Session, activity: Activity) -> str:
    """Best-effort: name the first not-yet-complete predecessor, if the
    dependency graph explains the block. Falls back to a generic label —
    "blocked" isn't a structured reason field on Activity, just a status."""
    incoming = db.scalars(
        select(Dependency).where(
            Dependency.successor_type == SchedulableType.ACTIVITY,
            Dependency.successor_id == activity.id,
        )
    ).all()
    for dep in incoming:
        if dep.predecessor_type == SchedulableType.ACTIVITY:
            predecessor = db.get(Activity, dep.predecessor_id)
            if predecessor is not None and predecessor.status != ActivityStatus.COMPLETED:
                return f"Blocked by {predecessor.title}"
        else:
            predecessor_m = db.get(Milestone, dep.predecessor_id)
            if predecessor_m is not None and predecessor_m.status != MilestoneStatus.COMPLETED:
                return f"Blocked by {predecessor_m.title}"
    return "Blocked"


def get_dashboard_summary(db: Session, project_id: int) -> DashboardSummary:
    today = dt.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    monday, sunday = _week_bounds(today)

    active_tasks = _count(
        db,
        select(Activity).where(
            Activity.project_id == project_id, Activity.status == ActivityStatus.IN_PROGRESS
        ),
    )
    milestones_this_week = _count(
        db,
        select(Milestone).where(
            Milestone.project_id == project_id,
            Milestone.date >= monday,
            Milestone.date <= sunday,
        ),
    )
    delayed = _count(
        db,
        select(Activity).where(
            Activity.project_id == project_id, Activity.status == ActivityStatus.DELAYED
        ),
    )
    blocked = _count(
        db,
        select(Activity).where(
            Activity.project_id == project_id, Activity.status == ActivityStatus.BLOCKED
        ),
    )
    social_activities = _count(
        db,
        select(CalendarEvent).where(
            CalendarEvent.project_id == project_id,
            CalendarEvent.event_type == CalendarEventType.SOCIAL,
            CalendarEvent.end_datetime >= monday,
            CalendarEvent.start_datetime <= sunday,
        ),
    )
    meetings = _count(
        db,
        select(CalendarEvent).where(
            CalendarEvent.project_id == project_id,
            CalendarEvent.event_type == CalendarEventType.MEETING,
            CalendarEvent.end_datetime >= monday,
            CalendarEvent.start_datetime <= sunday,
        ),
    )
    upcoming_deadlines = _count(
        db,
        select(CalendarEvent).where(
            CalendarEvent.project_id == project_id,
            CalendarEvent.event_type == CalendarEventType.DEADLINE,
            CalendarEvent.end_datetime >= monday,
            CalendarEvent.start_datetime <= sunday,
        ),
    )

    week_counts = WeekCounts(
        active_tasks=active_tasks,
        milestones_this_week=milestones_this_week,
        delayed=delayed,
        blocked=blocked,
        social_activities=social_activities,
        meetings=meetings,
        upcoming_deadlines=upcoming_deadlines,
    )

    upcoming_milestone_rows = db.scalars(
        select(Milestone)
        .where(
            Milestone.project_id == project_id,
            Milestone.date >= today,
            Milestone.status.not_in([MilestoneStatus.COMPLETED, MilestoneStatus.MISSED]),
        )
        .order_by(Milestone.date)
        .limit(UPCOMING_MILESTONES_LIMIT)
    ).all()
    upcoming_milestones = [
        UpcomingMilestone(
            id=m.id, title=m.title, date=m.date, team=m.team.name if m.team else None
        )
        for m in upcoming_milestone_rows
    ]

    delayed_rows = db.scalars(
        select(Activity)
        .where(Activity.project_id == project_id, Activity.status == ActivityStatus.DELAYED)
        .order_by(Activity.end_date)
    ).all()
    blocked_rows = db.scalars(
        select(Activity)
        .where(Activity.project_id == project_id, Activity.status == ActivityStatus.BLOCKED)
        .order_by(Activity.title)
    ).all()

    attention_required: list[AttentionItem] = []
    for activity in delayed_rows:
        days_late = max((today - activity.end_date).days, 0)
        detail = f"{days_late} day{'s' if days_late != 1 else ''} delayed" if days_late else "Delayed"
        attention_required.append(
            AttentionItem(id=activity.id, title=activity.title, status=activity.status, detail=detail)
        )
    for activity in blocked_rows:
        attention_required.append(
            AttentionItem(
                id=activity.id,
                title=activity.title,
                status=activity.status,
                detail=_blocked_detail(db, activity),
            )
        )

    return DashboardSummary(
        iso_year=iso_year,
        iso_week=iso_week,
        week_start=monday,
        week_end=sunday,
        week_counts=week_counts,
        upcoming_milestones=upcoming_milestones,
        attention_required=attention_required,
    )
