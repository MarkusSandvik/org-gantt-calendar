"""Idempotent demo data seed. Run with: python -m app.db.seed

Seeded accounts all share one development-only password (see
Settings.dev_seed_password / APP_DEV_SEED_PASSWORD) — never use this
seed script against anything but a local/dev database."""

import datetime as dt

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
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
    ("Mechanical", TeamCategory.HARDWARE),
    ("Electrical", TeamCategory.HARDWARE),
    ("Embedded", TeamCategory.HARDWARE),
    ("Perception", TeamCategory.SOFTWARE),
    ("Autonomy", TeamCategory.SOFTWARE),
    ("Control", TeamCategory.SOFTWARE),
    ("GUI", TeamCategory.SOFTWARE),
    ("Marketing", TeamCategory.ORGANIZATION),
    ("Web", TeamCategory.ORGANIZATION),
    ("Finance", TeamCategory.ORGANIZATION),
    ("Admin", TeamCategory.ORGANIZATION),
]

TAG_NAMES = [
    "Recruitment",
    "Sponsor",
    "Social",
    "Testing",
    "Competition",
    "Event",
    "Workshop",
    "Meeting",
    "Travel",
    "Deadline",
    "Internal",
    "External",
]

# (name, email, global_role) — the original five demo users. Team
# memberships for these are assigned below, separately from the newer
# role-descriptive example accounts Section 21 of the RBAC plan asks for.
USER_DEFS = [
    ("Markus", "markus@example.org", GlobalRole.ADMIN),
    ("Kari", "kari@example.org", GlobalRole.USER),
    ("Ola", "ola@example.org", GlobalRole.USER),
    ("Thomas", "thomas@example.org", GlobalRole.USER),
    ("Emil", "emil@example.org", GlobalRole.USER),
]

# (name, email, global_role) — role-descriptive accounts for exercising
# the Admin/Lead/Member hierarchy in local development.
EXAMPLE_USER_DEFS = [
    ("Admin User", "admin@example.local", GlobalRole.ADMIN),
    ("Embedded Lead", "embedded.lead@example.local", GlobalRole.USER),
    ("Mechanical Lead", "mechanical.lead@example.local", GlobalRole.USER),
    ("Embedded Member", "embedded.member@example.local", GlobalRole.USER),
    ("Mechanical Member", "mechanical.member@example.local", GlobalRole.USER),
]

# (email, team_name, team_role) memberships for the accounts above.
EXAMPLE_MEMBERSHIP_DEFS = [
    ("embedded.lead@example.local", "Embedded", TeamRole.LEAD),
    ("mechanical.lead@example.local", "Mechanical", TeamRole.LEAD),
    ("embedded.member@example.local", "Embedded", TeamRole.MEMBER),
    ("mechanical.member@example.local", "Mechanical", TeamRole.MEMBER),
]

# (name, team_name) memberships for the original five demo users, so
# Lead/Member-scoped authorization has real data to check against for
# them too, not just the newer example accounts.
LEGACY_MEMBERSHIP_DEFS = [
    ("Kari", "Electrical", TeamRole.MEMBER),
    ("Ola", "Mechanical", TeamRole.MEMBER),
    ("Thomas", "Embedded", TeamRole.MEMBER),
    ("Emil", "Perception", TeamRole.MEMBER),
]


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Project).first() is not None:
            print("Seed skipped: data already present.")
            return

        project = Project(
            name="AUV 2026",
            description="Autonomous underwater vehicle competition project.",
            start_date=dt.date(2026, 8, 1),
            end_date=dt.date(2027, 6, 30),
            auto_scheduling_enabled=False,
        )
        db.add(project)
        db.flush()

        teams = {}
        for i, (name, category) in enumerate(TEAM_DEFS):
            team = Team(
                project_id=project.id, name=name, category=category, sort_order=i
            )
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

        users_by_email = {}
        for name, email, global_role in EXAMPLE_USER_DEFS:
            user = User(
                name=name,
                email=email,
                global_role=global_role,
                status=UserStatus.ACTIVE,
                password_hash=dev_password_hash,
            )
            db.add(user)
            users_by_email[email] = user
        db.flush()

        for name, team_name, team_role in LEGACY_MEMBERSHIP_DEFS:
            db.add(
                TeamMembership(
                    team_id=teams[team_name].id, user_id=users[name].id, team_role=team_role
                )
            )
        for email, team_name, team_role in EXAMPLE_MEMBERSHIP_DEFS:
            db.add(
                TeamMembership(
                    team_id=teams[team_name].id,
                    user_id=users_by_email[email].id,
                    team_role=team_role,
                )
            )

        def tag_entity(entity_type: TaggableType, entity_id: int, *tag_names: str) -> None:
            for tn in tag_names:
                db.add(
                    TagAssociation(
                        tag_id=tags[tn].id, entity_type=entity_type, entity_id=entity_id
                    )
                )

        # Activities forming a realistic dependency chain, plus a couple of
        # delayed/blocked activities for dashboard "attention required" demo.
        pcb_design = Activity(
            project_id=project.id,
            title="PCB Design",
            description="Schematic and layout for the main control board.",
            start_date=dt.date(2026, 8, 10),
            end_date=dt.date(2026, 9, 4),
            status=ActivityStatus.COMPLETED,
            progress_percent=100,
            priority=Priority.HIGH,
            owner_team_id=teams["Electrical"].id,
            owner_user_id=users["Kari"].id,
            created_by_id=users["Markus"].id,
        )
        pcb_assembly = Activity(
            project_id=project.id,
            title="PCB Assembly",
            description="Populate and solder the produced boards.",
            start_date=dt.date(2026, 9, 8),
            end_date=dt.date(2026, 9, 25),
            status=ActivityStatus.IN_PROGRESS,
            progress_percent=60,
            priority=Priority.HIGH,
            owner_team_id=teams["Electrical"].id,
            owner_user_id=users["Kari"].id,
            created_by_id=users["Markus"].id,
        )
        system_integration = Activity(
            project_id=project.id,
            title="System Integration",
            description="Integrate electrical, embedded and mechanical subsystems.",
            start_date=dt.date(2026, 9, 28),
            end_date=dt.date(2026, 10, 20),
            status=ActivityStatus.NOT_STARTED,
            progress_percent=0,
            priority=Priority.CRITICAL,
            owner_team_id=teams["Embedded"].id,
            owner_user_id=users["Thomas"].id,
            created_by_id=users["Markus"].id,
        )
        pool_test = Activity(
            project_id=project.id,
            title="Pool Test",
            description="First in-water functional test.",
            start_date=dt.date(2026, 10, 22),
            end_date=dt.date(2026, 10, 24),
            status=ActivityStatus.NOT_STARTED,
            progress_percent=0,
            priority=Priority.HIGH,
            owner_team_id=teams["Mechanical"].id,
            owner_user_id=users["Ola"].id,
            created_by_id=users["Markus"].id,
        )
        computer_vision = Activity(
            project_id=project.id,
            title="Computer Vision",
            description="Object detection pipeline for gate and buoy tasks.",
            start_date=dt.date(2026, 8, 15),
            end_date=dt.date(2026, 10, 15),
            status=ActivityStatus.IN_PROGRESS,
            progress_percent=35,
            priority=Priority.NORMAL,
            owner_team_id=teams["Perception"].id,
            owner_user_id=users["Emil"].id,
            created_by_id=users["Markus"].id,
        )
        pressure_housing = Activity(
            project_id=project.id,
            title="Pressure Housing Design",
            description="Design of the watertight electronics housing.",
            start_date=dt.date(2026, 8, 5),
            end_date=dt.date(2026, 9, 20),
            status=ActivityStatus.IN_PROGRESS,
            progress_percent=65,
            priority=Priority.NORMAL,
            owner_team_id=teams["Mechanical"].id,
            owner_user_id=users["Ola"].id,
            created_by_id=users["Markus"].id,
        )
        battery_enclosure = Activity(
            project_id=project.id,
            title="Battery Enclosure",
            description="Enclosure for the battery pack, delayed due to part availability.",
            start_date=dt.date(2026, 8, 1),
            end_date=dt.date(2026, 8, 29),
            status=ActivityStatus.DELAYED,
            progress_percent=40,
            priority=Priority.HIGH,
            owner_team_id=teams["Mechanical"].id,
            owner_user_id=users["Ola"].id,
            created_by_id=users["Markus"].id,
        )
        can_integration = Activity(
            project_id=project.id,
            title="CAN Integration",
            description="Blocked by PCB delivery.",
            start_date=dt.date(2026, 9, 10),
            end_date=dt.date(2026, 9, 24),
            status=ActivityStatus.BLOCKED,
            progress_percent=10,
            priority=Priority.HIGH,
            owner_team_id=teams["Embedded"].id,
            owner_user_id=users["Thomas"].id,
            created_by_id=users["Markus"].id,
        )
        mechanical_manufacturing = Activity(
            project_id=project.id,
            title="Mechanical Manufacturing",
            description="CNC machining of structural parts.",
            start_date=dt.date(2026, 8, 20),
            end_date=dt.date(2026, 9, 18),
            status=ActivityStatus.DELAYED,
            progress_percent=45,
            priority=Priority.NORMAL,
            owner_team_id=teams["Mechanical"].id,
            owner_user_id=users["Ola"].id,
            created_by_id=users["Markus"].id,
        )

        activities = [
            pcb_design,
            pcb_assembly,
            system_integration,
            pool_test,
            computer_vision,
            pressure_housing,
            battery_enclosure,
            can_integration,
            mechanical_manufacturing,
        ]
        db.add_all(activities)
        db.flush()

        db.add_all(
            [
                ActivityContributor(activity_id=pressure_housing.id, user_id=users["Kari"].id),
                ActivityContributor(activity_id=pressure_housing.id, user_id=users["Thomas"].id),
                ActivityContributor(activity_id=pressure_housing.id, user_id=users["Emil"].id),
                ActivityContributor(activity_id=computer_vision.id, user_id=users["Markus"].id),
            ]
        )

        tag_entity(TaggableType.ACTIVITY, pressure_housing.id, "Testing")
        tag_entity(TaggableType.ACTIVITY, pcb_assembly.id, "Testing")
        tag_entity(TaggableType.ACTIVITY, pool_test.id, "Testing", "Competition")
        tag_entity(TaggableType.ACTIVITY, computer_vision.id, "Competition")

        db.add_all(
            [
                Dependency(
                    predecessor_type=SchedulableType.ACTIVITY,
                    predecessor_id=pcb_design.id,
                    successor_type=SchedulableType.ACTIVITY,
                    successor_id=pcb_assembly.id,
                    dependency_type=DependencyType.FINISH_TO_START,
                    lag_days=2,
                ),
                Dependency(
                    predecessor_type=SchedulableType.ACTIVITY,
                    predecessor_id=pcb_assembly.id,
                    successor_type=SchedulableType.ACTIVITY,
                    successor_id=system_integration.id,
                    dependency_type=DependencyType.FINISH_TO_START,
                    lag_days=1,
                ),
                Dependency(
                    predecessor_type=SchedulableType.ACTIVITY,
                    predecessor_id=system_integration.id,
                    successor_type=SchedulableType.ACTIVITY,
                    successor_id=pool_test.id,
                    dependency_type=DependencyType.FINISH_TO_START,
                    lag_days=1,
                ),
            ]
        )

        milestones = [
            Milestone(
                project_id=project.id,
                title="Architecture Freeze",
                date=dt.date(2026, 9, 18),
                team_id=teams["Embedded"].id,
                owner_user_id=users["Markus"].id,
                status=MilestoneStatus.ON_TRACK,
            ),
            Milestone(
                project_id=project.id,
                title="Electronics Prototype",
                date=dt.date(2026, 10, 12),
                team_id=teams["Electrical"].id,
                owner_user_id=users["Kari"].id,
                status=MilestoneStatus.ON_TRACK,
            ),
            Milestone(
                project_id=project.id,
                title="First Integration",
                date=dt.date(2026, 11, 4),
                team_id=teams["Embedded"].id,
                owner_user_id=users["Thomas"].id,
                status=MilestoneStatus.NOT_STARTED,
            ),
            Milestone(
                project_id=project.id,
                title="Drone in Water",
                date=dt.date(2027, 1, 18),
                team_id=teams["Mechanical"].id,
                owner_user_id=users["Ola"].id,
                status=MilestoneStatus.NOT_STARTED,
            ),
        ]
        db.add_all(milestones)

        # Calendar events for the week of 7-11 Sep 2026 (Mon-Fri), matching
        # the spec's example weekly schedule.
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

        mon, tue, wed, thu, fri = (dt.date(2026, 9, 7 + i) for i in range(5))
        db.add_all(
            [
                event("Embedded weekly meeting", CalendarEventType.MEETING, mon, 16, 17, "Embedded"),
                event("PCB assembly", CalendarEventType.WORKSHOP, tue, 10, 15, "Electrical"),
                event("Board meeting", CalendarEventType.MEETING, tue, 18, 20),
                event("Social: Team dinner", CalendarEventType.SOCIAL, wed, 19, 22),
                event("Pool testing", CalendarEventType.OTHER, thu, 9, 13, "Mechanical"),
                event("Sponsor presentation", CalendarEventType.SPONSOR, fri, 12, 13),
            ]
        )

        db.commit()
        print("Seed complete.")
        print(
            f"All seeded accounts share the development-only password: "
            f"{get_settings().dev_seed_password!r} (see APP_DEV_SEED_PASSWORD)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
