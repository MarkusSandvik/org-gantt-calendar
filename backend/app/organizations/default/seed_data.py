"""Neutral demo data for the generic "Example Organization" profile — lets
the platform boot and demonstrate scheduling/collaboration features with
zero Vortex-specific assets. See app/db/seed.py for the generic engine
that calls seed(db); this module owns only what data gets seeded.

Seeded accounts all share one development-only password (see
Settings.dev_seed_password / APP_DEV_SEED_PASSWORD) — never use this
seed data against anything but a local/dev database.
"""

import datetime as dt

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.activity import Activity, ActivityContributor
from app.models.calendar_event import CalendarEvent
from app.models.dependency import Dependency
from app.models.enums import (
    ActivityStatus,
    CalendarEventType,
    DependencyType,
    GlobalRole,
    MilestoneStatus,
    Priority,
    SchedulableType,
    TaggableType,
    TeamCategory,
    TeamRole,
    UserStatus,
)
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.tag import Tag, TagAssociation
from app.models.team import Team, TeamMembership
from app.models.user import User

TEAM_DEFS = [
    ("Engineering", TeamCategory.SOFTWARE),
    ("Design", TeamCategory.HARDWARE),
    ("Operations", TeamCategory.ORGANIZATION),
    ("Board", TeamCategory.ORGANIZATION),
]

TAG_NAMES = [
    "Planning",
    "Review",
    "Testing",
    "Internal",
    "External",
]

USER_DEFS = [
    ("Admin User", "admin@example.org", GlobalRole.ADMIN),
    ("Alice", "alice@example.org", GlobalRole.USER),
    ("Bob", "bob@example.org", GlobalRole.USER),
    ("Carol", "carol@example.org", GlobalRole.USER),
]

# (name, team_name, team_role) memberships for the demo users above.
MEMBERSHIP_DEFS = [
    ("Alice", "Engineering", TeamRole.LEAD),
    ("Bob", "Design", TeamRole.LEAD),
    ("Carol", "Operations", TeamRole.MEMBER),
]


def seed(db: Session) -> None:
    project = Project(
        name="Sample Project",
        description="Example project demonstrating scheduling and collaboration features.",
        start_date=dt.date(2026, 1, 1),
        end_date=dt.date(2026, 12, 31),
        auto_scheduling_enabled=False,
    )
    db.add(project)
    db.flush()

    teams = {}
    for i, (name, category) in enumerate(TEAM_DEFS):
        team = Team(project_id=project.id, name=name, category=category, sort_order=i)
        db.add(team)
        teams[name] = team
    db.flush()

    tags = {}
    for name in TAG_NAMES:
        tag = Tag(project_id=project.id, name=name)
        db.add(tag)
        tags[name] = tag
    db.flush()

    dev_password_hash = hash_password(get_settings().dev_seed_password)

    users = {}
    for name, email, global_role in USER_DEFS:
        user = User(
            name=name,
            email=email,
            global_role=global_role,
            status=UserStatus.ACTIVE,
            password_hash=dev_password_hash,
        )
        db.add(user)
        users[name] = user
    db.flush()

    for name, team_name, team_role in MEMBERSHIP_DEFS:
        db.add(
            TeamMembership(
                team_id=teams[team_name].id, user_id=users[name].id, team_role=team_role
            )
        )

    def tag_entity(entity_type: TaggableType, entity_id: int, *tag_names: str) -> None:
        for tn in tag_names:
            db.add(
                TagAssociation(tag_id=tags[tn].id, entity_type=entity_type, entity_id=entity_id)
            )

    design = Activity(
        project_id=project.id,
        title="Requirements Design",
        description="Define scope and requirements for the sample project.",
        start_date=dt.date(2026, 1, 5),
        end_date=dt.date(2026, 1, 23),
        status=ActivityStatus.COMPLETED,
        progress_percent=100,
        priority=Priority.HIGH,
        owner_team_id=teams["Engineering"].id,
        owner_user_id=users["Alice"].id,
        created_by_id=users["Admin User"].id,
    )
    build = Activity(
        project_id=project.id,
        title="Build Prototype",
        description="Implement a working prototype based on the requirements.",
        start_date=dt.date(2026, 1, 26),
        end_date=dt.date(2026, 3, 6),
        status=ActivityStatus.IN_PROGRESS,
        progress_percent=45,
        priority=Priority.HIGH,
        owner_team_id=teams["Engineering"].id,
        owner_user_id=users["Alice"].id,
        created_by_id=users["Admin User"].id,
    )
    review = Activity(
        project_id=project.id,
        title="Design Review",
        description="Review the prototype against the original requirements.",
        start_date=dt.date(2026, 3, 9),
        end_date=dt.date(2026, 3, 13),
        status=ActivityStatus.NOT_STARTED,
        progress_percent=0,
        priority=Priority.NORMAL,
        owner_team_id=teams["Design"].id,
        owner_user_id=users["Bob"].id,
        created_by_id=users["Admin User"].id,
    )
    rollout = Activity(
        project_id=project.id,
        title="Operational Rollout",
        description="Roll out the finished project to end users.",
        start_date=dt.date(2026, 3, 16),
        end_date=dt.date(2026, 4, 10),
        status=ActivityStatus.DELAYED,
        progress_percent=10,
        priority=Priority.NORMAL,
        owner_team_id=teams["Operations"].id,
        owner_user_id=users["Carol"].id,
        created_by_id=users["Admin User"].id,
    )

    activities = [design, build, review, rollout]
    db.add_all(activities)
    db.flush()

    db.add_all(
        [
            ActivityContributor(activity_id=build.id, user_id=users["Bob"].id),
            ActivityContributor(activity_id=review.id, user_id=users["Alice"].id),
        ]
    )

    tag_entity(TaggableType.ACTIVITY, design.id, "Planning")
    tag_entity(TaggableType.ACTIVITY, review.id, "Review", "Testing")

    db.add_all(
        [
            Dependency(
                predecessor_type=SchedulableType.ACTIVITY,
                predecessor_id=design.id,
                successor_type=SchedulableType.ACTIVITY,
                successor_id=build.id,
                dependency_type=DependencyType.FINISH_TO_START,
                lag_days=1,
            ),
            Dependency(
                predecessor_type=SchedulableType.ACTIVITY,
                predecessor_id=build.id,
                successor_type=SchedulableType.ACTIVITY,
                successor_id=review.id,
                dependency_type=DependencyType.FINISH_TO_START,
                lag_days=1,
            ),
        ]
    )

    milestones = [
        Milestone(
            project_id=project.id,
            title="Requirements Signed Off",
            date=dt.date(2026, 1, 23),
            team_id=teams["Engineering"].id,
            owner_user_id=users["Alice"].id,
            status=MilestoneStatus.ON_TRACK,
        ),
        Milestone(
            project_id=project.id,
            title="Prototype Ready",
            date=dt.date(2026, 3, 6),
            team_id=teams["Engineering"].id,
            owner_user_id=users["Alice"].id,
            status=MilestoneStatus.NOT_STARTED,
        ),
    ]
    db.add_all(milestones)

    def event(
        title: str,
        event_type: CalendarEventType,
        day: dt.date,
        start_hour: int,
        end_hour: int,
        team: str | None = None,
    ) -> CalendarEvent:
        return CalendarEvent(
            project_id=project.id,
            title=title,
            event_type=event_type,
            start_datetime=dt.datetime.combine(day, dt.time(start_hour, 0)),
            end_datetime=dt.datetime.combine(day, dt.time(end_hour, 0)),
            team_id=teams[team].id if team else None,
        )

    mon, wed = dt.date(2026, 1, 12), dt.date(2026, 1, 14)
    db.add_all(
        [
            event("Engineering weekly sync", CalendarEventType.MEETING, mon, 9, 10, "Engineering"),
            event("Prototype workshop", CalendarEventType.WORKSHOP, wed, 13, 16, "Design"),
        ]
    )
