import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import GlobalRole, TeamCategory, TeamRole, UserStatus
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User

PASSWORD = "admin-test-password-123"


@pytest.fixture()
def admin_world(db_session: Session):
    project = Project(name="P")
    embedded = Team(project=project, name="Embedded", category=TeamCategory.HARDWARE)
    mechanical = Team(project=project, name="Mechanical", category=TeamCategory.HARDWARE)
    db_session.add_all([project, embedded, mechanical])
    db_session.commit()

    def make(name: str, email: str, global_role: GlobalRole = GlobalRole.USER) -> User:
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

    lead = make("Lead", "lead@admin.test")
    member = make("Member", "member@admin.test")
    other_member = make("Other Member", "other.member@admin.test")

    db_session.add_all(
        [
            TeamMembership(team_id=embedded.id, user_id=lead.id, team_role=TeamRole.LEAD),
            TeamMembership(team_id=embedded.id, user_id=member.id, team_role=TeamRole.MEMBER),
            TeamMembership(
                team_id=mechanical.id, user_id=other_member.id, team_role=TeamRole.MEMBER
            ),
        ]
    )
    db_session.commit()

    return {
        "project": project,
        "embedded": embedded,
        "mechanical": mechanical,
        "lead": lead,
        "member": member,
        "other_member": other_member,
    }


def test_admin_sees_all_users(client: TestClient, admin_world: dict) -> None:
    response = client.get("/api/v1/users/admin")
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert {"lead@admin.test", "member@admin.test", "other.member@admin.test"} <= emails


def test_lead_sees_only_own_group_members(
    client: TestClient, admin_world: dict, as_user
) -> None:
    as_user(client, "lead@admin.test", PASSWORD)
    response = client.get("/api/v1/users/admin")
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert emails == {"member@admin.test"}


def test_member_cannot_view_user_admin_listing(
    client: TestClient, admin_world: dict, as_user
) -> None:
    as_user(client, "member@admin.test", PASSWORD)
    response = client.get("/api/v1/users/admin")
    assert response.status_code == 403


def test_admin_can_deactivate_and_reactivate_any_user(
    client: TestClient, admin_world: dict
) -> None:
    deactivate = client.post(f"/api/v1/users/{admin_world['member'].id}/deactivate")
    assert deactivate.status_code == 200
    assert deactivate.json()["status"] == "inactive"

    reactivate = client.post(f"/api/v1/users/{admin_world['member'].id}/reactivate")
    assert reactivate.status_code == 200
    assert reactivate.json()["status"] == "active"


def test_lead_can_deactivate_own_group_member(
    client: TestClient, admin_world: dict, as_user
) -> None:
    as_user(client, "lead@admin.test", PASSWORD)
    response = client.post(f"/api/v1/users/{admin_world['member'].id}/deactivate")
    assert response.status_code == 200


def test_lead_cannot_deactivate_another_groups_member(
    client: TestClient, admin_world: dict, as_user
) -> None:
    as_user(client, "lead@admin.test", PASSWORD)
    response = client.post(f"/api/v1/users/{admin_world['other_member'].id}/deactivate")
    assert response.status_code == 403


def test_deactivated_user_cannot_log_in(client: TestClient, admin_world: dict) -> None:
    client.post(f"/api/v1/users/{admin_world['member'].id}/deactivate")
    login = client.post(
        "/api/v1/auth/login", json={"email": "member@admin.test", "password": PASSWORD}
    )
    assert login.status_code == 401


def test_cannot_deactivate_own_account(client: TestClient, db_session: Session) -> None:
    me = client.get("/api/v1/auth/me").json()
    response = client.post(f"/api/v1/users/{me['id']}/deactivate")
    assert response.status_code == 400


def test_admin_can_promote_member_to_lead(client: TestClient, admin_world: dict) -> None:
    response = client.put(
        f"/api/v1/users/{admin_world['other_member'].id}/team-memberships",
        json={"team_id": admin_world["mechanical"].id, "team_role": "lead"},
    )
    assert response.status_code == 200, response.text
    membership = next(
        m
        for m in response.json()["team_memberships"]
        if m["team_id"] == admin_world["mechanical"].id
    )
    assert membership["team_role"] == "lead"


def test_promoting_to_lead_of_a_new_team_demotes_previous_lead_team(
    client: TestClient, admin_world: dict
) -> None:
    # The existing Lead (of Embedded) is reassigned to lead Mechanical —
    # their Embedded membership should drop to Member, not stay Lead too.
    response = client.put(
        f"/api/v1/users/{admin_world['lead'].id}/team-memberships",
        json={"team_id": admin_world["mechanical"].id, "team_role": "lead"},
    )
    assert response.status_code == 200, response.text
    memberships = {m["team_id"]: m["team_role"] for m in response.json()["team_memberships"]}
    assert memberships[admin_world["mechanical"].id] == "lead"
    assert memberships[admin_world["embedded"].id] == "member"


def test_admin_can_demote_lead_to_member(client: TestClient, admin_world: dict) -> None:
    response = client.put(
        f"/api/v1/users/{admin_world['lead'].id}/team-memberships",
        json={"team_id": admin_world["embedded"].id, "team_role": "member"},
    )
    assert response.status_code == 200, response.text
    membership = next(
        m
        for m in response.json()["team_memberships"]
        if m["team_id"] == admin_world["embedded"].id
    )
    assert membership["team_role"] == "member"


def test_admin_can_move_member_to_another_team(client: TestClient, admin_world: dict) -> None:
    remove = client.delete(
        f"/api/v1/users/{admin_world['member'].id}/team-memberships/{admin_world['embedded'].id}"
    )
    assert remove.status_code == 204

    add = client.put(
        f"/api/v1/users/{admin_world['member'].id}/team-memberships",
        json={"team_id": admin_world["mechanical"].id, "team_role": "member"},
    )
    assert add.status_code == 200, add.text
    team_ids = {m["team_id"] for m in add.json()["team_memberships"]}
    assert team_ids == {admin_world["mechanical"].id}


def test_lead_cannot_change_team_memberships(
    client: TestClient, admin_world: dict, as_user
) -> None:
    as_user(client, "lead@admin.test", PASSWORD)
    response = client.put(
        f"/api/v1/users/{admin_world['member'].id}/team-memberships",
        json={"team_id": admin_world["embedded"].id, "team_role": "lead"},
    )
    assert response.status_code == 403


def test_admin_can_change_global_role(client: TestClient, admin_world: dict) -> None:
    response = client.patch(
        f"/api/v1/users/{admin_world['member'].id}/global-role",
        json={"global_role": "admin"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["global_role"] == "admin"


def test_lead_cannot_change_global_role(
    client: TestClient, admin_world: dict, as_user
) -> None:
    as_user(client, "lead@admin.test", PASSWORD)
    response = client.patch(
        f"/api/v1/users/{admin_world['member'].id}/global-role",
        json={"global_role": "admin"},
    )
    assert response.status_code == 403


def test_cannot_change_own_global_role(client: TestClient) -> None:
    me = client.get("/api/v1/auth/me").json()
    response = client.patch(
        f"/api/v1/users/{me['id']}/global-role", json={"global_role": "user"}
    )
    assert response.status_code == 400
