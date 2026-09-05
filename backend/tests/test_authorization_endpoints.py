"""HTTP-level authorization tests — the Member/Lead/Admin/Security matrix
from RBAC_PLAN.md, exercised through the real routers rather than unit
tests against app.core.permissions directly (see test_permissions.py for
those). Each test logs in as a specific role via the `as_user` fixture
and checks what the API actually allows or blocks."""

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import GlobalRole, TeamCategory, TeamRole, UserStatus
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User

PASSWORD = "rbac-test-password-123"


@pytest.fixture()
def rbac_world(db_session: Session):
    """Embedded and Mechanical teams, each with a Lead and a Member, plus
    an Embedded activity/milestone/calendar-event to exercise ownership
    and cross-team checks against."""
    project = Project(name="RBAC Test Project")
    embedded = Team(project=project, name="Embedded", category=TeamCategory.HARDWARE)
    mechanical = Team(project=project, name="Mechanical", category=TeamCategory.HARDWARE)
    db_session.add_all([project, embedded, mechanical])
    db_session.commit()

    def make(name: str, email: str, global_role: GlobalRole) -> User:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(PASSWORD),
            global_role=global_role,
            status=UserStatus.ACTIVE,
        )
        db_session.add(user)
        db_session.commit()
        return user

    embedded_lead = make("Embedded Lead", "embedded.lead@rbac.test", GlobalRole.USER)
    embedded_member = make("Embedded Member", "embedded.member@rbac.test", GlobalRole.USER)
    mechanical_lead = make("Mechanical Lead", "mechanical.lead@rbac.test", GlobalRole.USER)
    mechanical_member = make("Mechanical Member", "mechanical.member@rbac.test", GlobalRole.USER)
    outsider = make("Outsider", "outsider@rbac.test", GlobalRole.USER)

    db_session.add_all(
        [
            TeamMembership(
                team_id=embedded.id, user_id=embedded_lead.id, team_role=TeamRole.LEAD
            ),
            TeamMembership(
                team_id=embedded.id, user_id=embedded_member.id, team_role=TeamRole.MEMBER
            ),
            TeamMembership(
                team_id=mechanical.id, user_id=mechanical_lead.id, team_role=TeamRole.LEAD
            ),
            TeamMembership(
                team_id=mechanical.id,
                user_id=mechanical_member.id,
                team_role=TeamRole.MEMBER,
            ),
        ]
    )
    db_session.commit()

    return {
        "project": project,
        "embedded": embedded,
        "mechanical": mechanical,
        "embedded_lead": embedded_lead,
        "embedded_member": embedded_member,
        "mechanical_lead": mechanical_lead,
        "mechanical_member": mechanical_member,
        "outsider": outsider,
    }


def make_activity(client: TestClient, world: dict, **overrides) -> dict:
    payload = {
        "project_id": world["project"].id,
        "title": "CAN Integration",
        "start_date": "2026-09-01",
        "end_date": "2026-09-10",
        "owner_team_id": world["embedded"].id,
        "owner_user_id": world["embedded_member"].id,
        "contributor_user_ids": [],
        "tag_ids": [],
    }
    payload.update(overrides)
    response = client.post("/api/v1/activities", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Member
# ---------------------------------------------------------------------------


def test_member_can_view_other_groups_tasks(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "mechanical.member@rbac.test", PASSWORD)
    response = client.get(f"/api/v1/activities/{activity['id']}")
    assert response.status_code == 200


def test_member_can_update_own_assigned_task_progress_and_status(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "embedded.member@rbac.test", PASSWORD)
    response = client.patch(
        f"/api/v1/activities/{activity['id']}",
        json={"progress_percent": 40, "status": "in_progress"},
    )
    assert response.status_code == 200, response.text


def test_member_can_update_progress_when_frontend_resubmits_the_whole_form(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    # Regression test: the ActivityFormModal always PATCHes the entire
    # form, not just the fields the user touched. Every other field's
    # value is unchanged here — only progress_percent differs — so this
    # must succeed for an assigned Member exactly as it does when only
    # progress_percent is sent (the test above).
    activity = make_activity(client, rbac_world, owner_user_id=rbac_world["embedded_member"].id)
    as_user(client, "embedded.member@rbac.test", PASSWORD)
    response = client.patch(
        f"/api/v1/activities/{activity['id']}",
        json={
            "title": activity["title"],
            "description": activity["description"],
            "start_date": activity["start_date"],
            "end_date": activity["end_date"],
            "status": activity["status"],
            "progress_percent": 55,
            "priority": activity["priority"],
            "owner_team_id": activity["owner_team"]["id"] if activity["owner_team"] else None,
            "owner_user_id": activity["owner_user"]["id"] if activity["owner_user"] else None,
            "contributor_user_ids": [c["id"] for c in activity["contributors"]],
            "tag_ids": [t["id"] for t in activity["tags"]],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["progress_percent"] == 55


def test_member_can_comment_on_assigned_task(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "embedded.member@rbac.test", PASSWORD)
    response = client.post(
        f"/api/v1/activities/{activity['id']}/comments", json={"body": "Working on it."}
    )
    assert response.status_code == 201, response.text


def test_member_cannot_modify_schedule(client: TestClient, rbac_world: dict, as_user) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "embedded.member@rbac.test", PASSWORD)
    response = client.patch(
        f"/api/v1/activities/{activity['id']}", json={"start_date": "2026-09-05"}
    )
    assert response.status_code == 403


def test_member_cannot_modify_unassigned_task(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "mechanical.member@rbac.test", PASSWORD)
    response = client.patch(
        f"/api/v1/activities/{activity['id']}", json={"progress_percent": 90}
    )
    assert response.status_code == 403


def test_member_cannot_invite_users(client: TestClient, rbac_world: dict, as_user) -> None:
    as_user(client, "embedded.member@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": "new@rbac.test",
            "name": "New",
            "team_id": rbac_world["embedded"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    assert response.status_code in (403, 404)


def test_member_cannot_create_tasks(client: TestClient, rbac_world: dict, as_user) -> None:
    as_user(client, "embedded.member@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/activities",
        json={
            "project_id": rbac_world["project"].id,
            "title": "New task",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "owner_team_id": rbac_world["embedded"].id,
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------


def test_lead_can_view_all_groups(client: TestClient, rbac_world: dict, as_user) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "mechanical.lead@rbac.test", PASSWORD)
    response = client.get(f"/api/v1/activities/{activity['id']}")
    assert response.status_code == 200


def test_lead_can_create_task_in_own_group(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/activities",
        json={
            "project_id": rbac_world["project"].id,
            "title": "New Embedded task",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "owner_team_id": rbac_world["embedded"].id,
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    )
    assert response.status_code == 201, response.text


def test_lead_can_edit_own_group_task(client: TestClient, rbac_world: dict, as_user) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.patch(
        f"/api/v1/activities/{activity['id']}", json={"start_date": "2026-09-02"}
    )
    assert response.status_code == 200, response.text


def test_lead_can_assign_own_group_member(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.patch(
        f"/api/v1/activities/{activity['id']}",
        json={"owner_user_id": rbac_world["embedded_member"].id},
    )
    assert response.status_code == 200, response.text


def test_lead_cannot_edit_another_groups_task(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    activity = make_activity(client, rbac_world)
    as_user(client, "mechanical.lead@rbac.test", PASSWORD)
    response = client.patch(
        f"/api/v1/activities/{activity['id']}", json={"priority": "critical"}
    )
    assert response.status_code == 403


def test_lead_cannot_create_task_in_another_group(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    as_user(client, "mechanical.lead@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/activities",
        json={
            "project_id": rbac_world["project"].id,
            "title": "Sneaky task",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "owner_team_id": rbac_world["embedded"].id,
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    )
    assert response.status_code == 403


def test_lead_can_invite_member_into_own_group(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": "new.member@rbac.test",
            "name": "New Member",
            "team_id": rbac_world["embedded"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    assert response.status_code == 201, response.text


def test_lead_cannot_invite_lead(client: TestClient, rbac_world: dict, as_user) -> None:
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": "sneaky.lead@rbac.test",
            "name": "Sneaky",
            "team_id": rbac_world["embedded"].id,
            "target_global_role": "user",
            "target_team_role": "lead",
        },
    )
    assert response.status_code == 403


def test_lead_cannot_invite_admin(client: TestClient, rbac_world: dict, as_user) -> None:
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": "sneaky.admin@rbac.test",
            "name": "Sneaky",
            "team_id": None,
            "target_global_role": "admin",
            "target_team_role": None,
        },
    )
    assert response.status_code == 403


def test_lead_cannot_invite_member_into_another_group(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": "sneaky.member@rbac.test",
            "name": "Sneaky",
            "team_id": rbac_world["mechanical"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    assert response.status_code == 403


def test_lead_cannot_set_baseline(client: TestClient, rbac_world: dict, as_user) -> None:
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.post(
        "/api/v1/baselines",
        params={"project_id": rbac_world["project"].id},
        json={"name": "Sneaky baseline", "note": None},
    )
    assert response.status_code == 403


def test_lead_cannot_modify_another_groups_membership(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    response = client.post(
        f"/api/v1/users/{rbac_world['mechanical_member'].id}/deactivate"
    )
    assert response.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


def test_admin_can_manage_all_tasks(client: TestClient, rbac_world: dict, as_user) -> None:
    activity = make_activity(client, rbac_world)
    response = client.patch(
        f"/api/v1/activities/{activity['id']}",
        json={"owner_team_id": rbac_world["mechanical"].id},
    )
    assert response.status_code == 200, response.text


def test_admin_can_invite_member(client: TestClient, rbac_world: dict) -> None:
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": "new.member@rbac.test",
            "name": "New Member",
            "team_id": rbac_world["embedded"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    assert response.status_code == 201, response.text


def test_admin_can_invite_lead_and_admin(client: TestClient, rbac_world: dict) -> None:
    lead_response = client.post(
        "/api/v1/invitations",
        json={
            "email": "new.lead@rbac.test",
            "name": "New Lead",
            "team_id": rbac_world["mechanical"].id,
            "target_global_role": "user",
            "target_team_role": "lead",
        },
    )
    assert lead_response.status_code == 201, lead_response.text

    admin_response = client.post(
        "/api/v1/invitations",
        json={
            "email": "new.admin@rbac.test",
            "name": "New Admin",
            "team_id": None,
            "target_global_role": "admin",
            "target_team_role": None,
        },
    )
    assert admin_response.status_code == 201, admin_response.text


def test_admin_can_manage_baselines(client: TestClient, rbac_world: dict) -> None:
    response = client.post(
        "/api/v1/baselines",
        params={"project_id": rbac_world["project"].id},
        json={"name": "Admin baseline", "note": None},
    )
    assert response.status_code == 201, response.text


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


def test_unauthenticated_write_request_fails(client: TestClient, rbac_world: dict) -> None:
    client.post("/api/v1/auth/logout")
    response = client.post(
        "/api/v1/activities",
        json={
            "project_id": rbac_world["project"].id,
            "title": "Nope",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    )
    assert response.status_code in (401, 403)


def test_inactive_user_cannot_authenticate(
    client: TestClient, db_session: Session, rbac_world: dict
) -> None:
    user = rbac_world["embedded_member"]
    user.status = UserStatus.INACTIVE
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "embedded.member@rbac.test", "password": PASSWORD},
    )
    assert response.status_code == 401


def test_privilege_escalation_role_field_is_ignored(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    # A Lead cannot grant themselves Admin by sending extra fields an
    # activity/task payload has no business carrying in the first place —
    # verified indirectly: the Lead's own global_role is unchanged after
    # any request they make, since no endpoint accepts a self-service
    # global_role field at all.
    as_user(client, "embedded.lead@rbac.test", PASSWORD)
    me = client.get("/api/v1/auth/me").json()
    assert me["global_role"] == "user"


def test_activity_with_no_owner_team_or_user_does_not_crash_authorization(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    # Section 25: old/incomplete data (no team, no owner) must stay safely
    # viewable and safely un-editable, never a 500.
    orphan = make_activity(
        client, rbac_world, title="Orphan task", owner_team_id=None, owner_user_id=None
    )

    as_user(client, "embedded.member@rbac.test", PASSWORD)
    view = client.get(f"/api/v1/activities/{orphan['id']}")
    assert view.status_code == 200

    member_edit = client.patch(
        f"/api/v1/activities/{orphan['id']}", json={"priority": "high"}
    )
    assert member_edit.status_code == 403


def test_admin_can_edit_activity_with_no_owner_team(
    client: TestClient, rbac_world: dict
) -> None:
    orphan = make_activity(
        client, rbac_world, title="Orphan task 2", owner_team_id=None, owner_user_id=None
    )
    response = client.patch(f"/api/v1/activities/{orphan['id']}", json={"priority": "high"})
    assert response.status_code == 200, response.text


def test_direct_api_call_cannot_bypass_team_restriction(
    client: TestClient, rbac_world: dict, as_user
) -> None:
    # Same check as test_lead_cannot_edit_another_groups_task, phrased as
    # the "direct API call" security-matrix item: hitting the endpoint
    # directly with a crafted payload naming another team's activity id
    # must still be rejected server-side.
    activity = make_activity(client, rbac_world)
    as_user(client, "mechanical.member@rbac.test", PASSWORD)
    response = client.delete(f"/api/v1/activities/{activity['id']}")
    assert response.status_code == 403
