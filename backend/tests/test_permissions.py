import datetime as dt

import pytest
from sqlalchemy.orm import Session

from app.core import permissions as perm
from app.models.activity import Activity, ActivityContributor
from app.models.calendar_event import CalendarEvent
from app.models.enums import (
    ActivityStatus,
    CalendarEventType,
    GlobalRole,
    MilestoneStatus,
    Priority,
    TeamCategory,
    TeamRole,
    UserStatus,
)
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User


@pytest.fixture()
def world(db_session: Session):
    """Two teams, an Admin, a Lead of Embedded, a Member of Embedded, a
    Member of Mechanical, and an activity/milestone/event owned by
    Embedded — the minimum shape every permission check below needs."""
    project = Project(name="P")
    embedded = Team(project=project, name="Embedded", category=TeamCategory.HARDWARE)
    mechanical = Team(project=project, name="Mechanical", category=TeamCategory.HARDWARE)
    admin = User(name="Admin", email="admin@x.org", global_role=GlobalRole.ADMIN)
    lead = User(name="Lead", email="lead@x.org", global_role=GlobalRole.USER)
    embedded_member = User(name="EMember", email="em@x.org", global_role=GlobalRole.USER)
    mechanical_member = User(name="MMember", email="mm@x.org", global_role=GlobalRole.USER)
    outsider = User(name="Outsider", email="out@x.org", global_role=GlobalRole.USER)
    db_session.add_all(
        [project, embedded, mechanical, admin, lead, embedded_member, mechanical_member, outsider]
    )
    db_session.commit()

    db_session.add_all(
        [
            TeamMembership(team_id=embedded.id, user_id=lead.id, team_role=TeamRole.LEAD),
            TeamMembership(
                team_id=embedded.id, user_id=embedded_member.id, team_role=TeamRole.MEMBER
            ),
            TeamMembership(
                team_id=mechanical.id, user_id=mechanical_member.id, team_role=TeamRole.MEMBER
            ),
        ]
    )
    db_session.commit()

    activity = Activity(
        project_id=project.id,
        title="CAN Integration",
        start_date=dt.date(2026, 9, 1),
        end_date=dt.date(2026, 9, 10),
        status=ActivityStatus.IN_PROGRESS,
        progress_percent=10,
        priority=Priority.NORMAL,
        owner_team_id=embedded.id,
        owner_user_id=embedded_member.id,
    )
    db_session.add(activity)
    db_session.commit()
    db_session.add(
        ActivityContributor(activity_id=activity.id, user_id=mechanical_member.id)
    )
    db_session.commit()

    milestone = Milestone(
        project_id=project.id,
        title="Architecture Freeze",
        date=dt.date(2026, 9, 18),
        team_id=embedded.id,
        owner_user_id=lead.id,
        status=MilestoneStatus.ON_TRACK,
    )
    org_wide_milestone = Milestone(
        project_id=project.id,
        title="Drone in Water",
        date=dt.date(2027, 1, 18),
        team_id=None,
        owner_user_id=admin.id,
        status=MilestoneStatus.NOT_STARTED,
    )
    event = CalendarEvent(
        project_id=project.id,
        title="Embedded sync",
        event_type=CalendarEventType.MEETING,
        start_datetime=dt.datetime(2026, 9, 7, 16, 0),
        end_datetime=dt.datetime(2026, 9, 7, 17, 0),
        team_id=embedded.id,
    )
    db_session.add_all([milestone, org_wide_milestone, event])
    db_session.commit()

    return {
        "project": project,
        "embedded": embedded,
        "mechanical": mechanical,
        "admin": admin,
        "lead": lead,
        "embedded_member": embedded_member,
        "mechanical_member": mechanical_member,
        "outsider": outsider,
        "activity": activity,
        "milestone": milestone,
        "org_wide_milestone": org_wide_milestone,
        "event": event,
    }


def test_get_led_team_id(db_session: Session, world) -> None:
    assert perm.get_led_team_id(db_session, world["lead"]) == world["embedded"].id
    assert perm.get_led_team_id(db_session, world["embedded_member"]) is None


def test_leads_team(db_session: Session, world) -> None:
    assert perm.leads_team(db_session, world["lead"], world["embedded"].id) is True
    assert perm.leads_team(db_session, world["lead"], world["mechanical"].id) is False
    assert perm.leads_team(db_session, world["lead"], None) is False


def test_is_assigned_to_activity_covers_owner_and_contributor(
    db_session: Session, world
) -> None:
    activity = world["activity"]
    assert perm.is_assigned_to_activity(db_session, world["embedded_member"], activity) is True
    assert perm.is_assigned_to_activity(db_session, world["mechanical_member"], activity) is True
    assert perm.is_assigned_to_activity(db_session, world["outsider"], activity) is False


def test_can_create_activity(db_session: Session, world) -> None:
    assert perm.can_create_activity(db_session, world["admin"], world["mechanical"].id) is True
    assert perm.can_create_activity(db_session, world["lead"], world["embedded"].id) is True
    assert perm.can_create_activity(db_session, world["lead"], world["mechanical"].id) is False
    assert (
        perm.can_create_activity(db_session, world["embedded_member"], world["embedded"].id)
        is False
    )


def test_can_edit_activity_is_admin_or_own_team_lead_only(db_session: Session, world) -> None:
    activity = world["activity"]
    assert perm.can_edit_activity(db_session, world["admin"], activity) is True
    assert perm.can_edit_activity(db_session, world["lead"], activity) is True
    # Assigned Member does NOT get full edit rights (schedule/priority/etc).
    assert perm.can_edit_activity(db_session, world["embedded_member"], activity) is False
    assert perm.can_edit_activity(db_session, world["mechanical_member"], activity) is False


def test_member_can_update_only_status_and_progress_on_assigned_activity(
    db_session: Session, world
) -> None:
    activity = world["activity"]
    member = world["embedded_member"]
    assert perm.can_update_activity_fields(db_session, member, activity, {"status"}) is True
    assert (
        perm.can_update_activity_fields(db_session, member, activity, {"progress_percent"})
        is True
    )
    assert (
        perm.can_update_activity_fields(
            db_session, member, activity, {"status", "progress_percent"}
        )
        is True
    )
    assert perm.can_update_activity_fields(db_session, member, activity, {"start_date"}) is False
    assert perm.can_update_activity_fields(db_session, member, activity, {"priority"}) is False


def test_unassigned_member_cannot_update_any_activity_field(db_session: Session, world) -> None:
    activity = world["activity"]
    assert (
        perm.can_update_activity_fields(db_session, world["outsider"], activity, {"status"})
        is False
    )


def test_lead_can_update_any_activity_field_in_own_team(db_session: Session, world) -> None:
    activity = world["activity"]
    assert (
        perm.can_update_activity_fields(
            db_session, world["lead"], activity, {"start_date", "priority", "owner_team_id"}
        )
        is True
    )


def test_lead_cannot_edit_or_update_another_teams_activity(db_session: Session, world) -> None:
    activity = world["activity"]  # owned by Embedded
    mechanical_lead = User(name="MLead", email="mlead@x.org", global_role=GlobalRole.USER)
    db_session.add(mechanical_lead)
    db_session.commit()
    db_session.add(
        TeamMembership(
            team_id=world["mechanical"].id, user_id=mechanical_lead.id, team_role=TeamRole.LEAD
        )
    )
    db_session.commit()

    assert perm.can_edit_activity(db_session, mechanical_lead, activity) is False
    assert (
        perm.can_update_activity_fields(db_session, mechanical_lead, activity, {"status"})
        is False
    )


def test_can_delete_activity_matches_can_edit_activity(db_session: Session, world) -> None:
    activity = world["activity"]
    assert perm.can_delete_activity(db_session, world["admin"], activity) is True
    assert perm.can_delete_activity(db_session, world["lead"], activity) is True
    assert perm.can_delete_activity(db_session, world["embedded_member"], activity) is False


def test_can_comment_on_activity(db_session: Session, world) -> None:
    activity = world["activity"]
    assert perm.can_comment_on_activity(db_session, world["admin"], activity) is True
    assert perm.can_comment_on_activity(db_session, world["lead"], activity) is True
    assert perm.can_comment_on_activity(db_session, world["embedded_member"], activity) is True
    assert perm.can_comment_on_activity(db_session, world["mechanical_member"], activity) is True
    assert perm.can_comment_on_activity(db_session, world["outsider"], activity) is False


def test_can_manage_milestone_team_scoped(db_session: Session, world) -> None:
    milestone = world["milestone"]
    assert perm.can_manage_milestone(db_session, world["admin"], milestone) is True
    assert perm.can_manage_milestone(db_session, world["lead"], milestone) is True
    assert perm.can_manage_milestone(db_session, world["embedded_member"], milestone) is False


def test_org_wide_milestone_is_admin_only(db_session: Session, world) -> None:
    milestone = world["org_wide_milestone"]
    assert perm.can_manage_milestone(db_session, world["admin"], milestone) is True
    assert perm.can_manage_milestone(db_session, world["lead"], milestone) is False


def test_can_manage_calendar_event(db_session: Session, world) -> None:
    event = world["event"]
    assert perm.can_manage_calendar_event(db_session, world["admin"], event) is True
    assert perm.can_manage_calendar_event(db_session, world["lead"], event) is True
    assert perm.can_manage_calendar_event(db_session, world["embedded_member"], event) is False


def test_lead_can_reference_another_teams_task_in_a_dependency(
    db_session: Session, world
) -> None:
    other_activity = Activity(
        project_id=world["project"].id,
        title="Power Distribution Ready",
        start_date=dt.date(2026, 8, 1),
        end_date=dt.date(2026, 8, 20),
        owner_team_id=world["mechanical"].id,
    )
    db_session.add(other_activity)
    db_session.commit()

    # Embedded Lead links their own CAN Integration task to Mechanical's
    # Power Distribution Ready task — allowed because Embedded owns one end.
    assert (
        perm.can_manage_dependency(
            db_session,
            world["lead"],
            "activity",
            other_activity.id,
            "activity",
            world["activity"].id,
        )
        is True
    )


def test_lead_cannot_create_dependency_touching_only_other_teams(
    db_session: Session, world
) -> None:
    a = Activity(
        project_id=world["project"].id,
        title="A",
        start_date=dt.date(2026, 8, 1),
        end_date=dt.date(2026, 8, 2),
        owner_team_id=world["mechanical"].id,
    )
    b = Activity(
        project_id=world["project"].id,
        title="B",
        start_date=dt.date(2026, 8, 3),
        end_date=dt.date(2026, 8, 4),
        owner_team_id=world["mechanical"].id,
    )
    db_session.add_all([a, b])
    db_session.commit()

    assert (
        perm.can_manage_dependency(db_session, world["lead"], "activity", a.id, "activity", b.id)
        is False
    )


def test_baseline_team_settings_are_admin_only(world) -> None:
    assert perm.can_manage_baseline(world["admin"]) is True
    assert perm.can_manage_baseline(world["lead"]) is False
    assert perm.can_manage_team(world["admin"]) is True
    assert perm.can_manage_team(world["lead"]) is False
    assert perm.can_manage_settings(world["admin"]) is True
    assert perm.can_manage_settings(world["lead"]) is False


def test_lead_can_deactivate_own_group_member_only(db_session: Session, world) -> None:
    assert (
        perm.can_deactivate_user(db_session, world["lead"], world["embedded_member"]) is True
    )
    assert (
        perm.can_deactivate_user(db_session, world["lead"], world["mechanical_member"]) is False
    )


def test_lead_cannot_deactivate_an_admin(db_session: Session, world) -> None:
    # Even a same-team membership shouldn't matter — target is an Admin.
    world["admin"].status = UserStatus.ACTIVE
    db_session.add(
        TeamMembership(
            team_id=world["embedded"].id, user_id=world["admin"].id, team_role=TeamRole.MEMBER
        )
    )
    db_session.commit()
    assert perm.can_deactivate_user(db_session, world["lead"], world["admin"]) is False


def test_require_raises_403_on_false(world) -> None:
    from app.core.permissions import PermissionDenied

    with pytest.raises(PermissionDenied):
        perm.require(False)
    perm.require(True)  # does not raise
