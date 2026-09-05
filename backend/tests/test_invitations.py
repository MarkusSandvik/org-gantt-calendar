import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import generate_token, hash_password, hash_token, utc_now
from app.models.enums import GlobalRole, InvitationStatus, TeamCategory, TeamRole, UserStatus
from app.models.invitation import Invitation
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User

PASSWORD = "invite-test-password-123"


@pytest.fixture()
def team_and_lead(db_session: Session):
    project = Project(name="P")
    team = Team(project=project, name="Embedded", category=TeamCategory.HARDWARE)
    lead = User(
        name="Lead",
        email="lead@invite.test",
        password_hash=hash_password(PASSWORD),
        global_role=GlobalRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([project, team, lead])
    db_session.commit()
    db_session.add(TeamMembership(team_id=team.id, user_id=lead.id, team_role=TeamRole.LEAD))
    db_session.commit()
    return {"project": project, "team": team, "lead": lead}


def test_create_invitation_returns_dev_invite_url(
    client: TestClient, team_and_lead: dict
) -> None:
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": "invitee@invite.test",
            "name": "Invitee",
            "team_id": team_and_lead["team"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["invite_url"] is not None
    assert "token=" in body["invite_url"]


def test_accept_invitation_creates_active_user_and_logs_in(
    client: TestClient, db_session: Session, team_and_lead: dict
) -> None:
    create_response = client.post(
        "/api/v1/invitations",
        json={
            "email": "invitee2@invite.test",
            "name": "Invitee Two",
            "team_id": team_and_lead["team"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    invite_url = create_response.json()["invite_url"]
    token = invite_url.split("token=")[1]

    preview = client.get(f"/api/v1/invitations/preview/{token}")
    assert preview.status_code == 200
    assert preview.json()["email"] == "invitee2@invite.test"
    assert preview.json()["team_name"] == "Embedded"

    client.post("/api/v1/auth/logout")
    accept = client.post(
        "/api/v1/invitations/accept",
        json={"token": token, "password": "brand-new-account-pw"},
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["email"] == "invitee2@invite.test"

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "invitee2@invite.test"
    assert me.json()["team_memberships"][0]["team_role"] == "member"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "invitee2@invite.test", "password": "brand-new-account-pw"},
    )
    assert login.status_code == 200


def test_invitation_token_is_single_use(client: TestClient, team_and_lead: dict) -> None:
    create_response = client.post(
        "/api/v1/invitations",
        json={
            "email": "invitee3@invite.test",
            "name": "Invitee Three",
            "team_id": team_and_lead["team"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    token = create_response.json()["invite_url"].split("token=")[1]

    first = client.post(
        "/api/v1/invitations/accept", json={"token": token, "password": "first-password-1"}
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/invitations/accept", json={"token": token, "password": "second-password-2"}
    )
    assert second.status_code == 400


def test_expired_invitation_cannot_be_accepted(
    client: TestClient, db_session: Session, team_and_lead: dict
) -> None:
    token = generate_token()
    db_session.add(
        Invitation(
            email="expired@invite.test",
            name="Expired",
            team_id=team_and_lead["team"].id,
            target_global_role=GlobalRole.USER,
            target_team_role=TeamRole.MEMBER,
            invited_by_user_id=team_and_lead["lead"].id,
            token_hash=hash_token(token),
            status=InvitationStatus.PENDING,
            expires_at=utc_now() - dt.timedelta(hours=1),
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/invitations/accept", json={"token": token, "password": "does-not-matter-1"}
    )
    assert response.status_code == 400


def test_revoked_invitation_cannot_be_accepted(
    client: TestClient, db_session: Session, team_and_lead: dict
) -> None:
    create_response = client.post(
        "/api/v1/invitations",
        json={
            "email": "revoke-me@invite.test",
            "name": "Revoke Me",
            "team_id": team_and_lead["team"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    body = create_response.json()
    token = body["invite_url"].split("token=")[1]
    invitation_id = body["id"]

    revoke = client.post(f"/api/v1/invitations/{invitation_id}/revoke")
    assert revoke.status_code == 204

    accept = client.post(
        "/api/v1/invitations/accept", json={"token": token, "password": "does-not-matter-2"}
    )
    assert accept.status_code == 400


def test_cannot_invite_an_email_that_already_has_an_account(
    client: TestClient, team_and_lead: dict
) -> None:
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": team_and_lead["lead"].email,
            "name": "Duplicate",
            "team_id": team_and_lead["team"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    assert response.status_code == 409


def test_lead_sees_only_own_team_invitations(
    client: TestClient, db_session: Session, team_and_lead: dict, as_user
) -> None:
    other_team = Team(
        project=team_and_lead["project"], name="Mechanical", category=TeamCategory.HARDWARE
    )
    other_lead = User(
        name="Other Lead",
        email="other.lead@invite.test",
        password_hash=hash_password(PASSWORD),
        global_role=GlobalRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([other_team, other_lead])
    db_session.commit()
    db_session.add(
        TeamMembership(team_id=other_team.id, user_id=other_lead.id, team_role=TeamRole.LEAD)
    )
    db_session.commit()

    client.post(
        "/api/v1/invitations",
        json={
            "email": "for.embedded@invite.test",
            "name": "For Embedded",
            "team_id": team_and_lead["team"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )

    as_user(client, "other.lead@invite.test", PASSWORD)
    client.post(
        "/api/v1/invitations",
        json={
            "email": "for.mechanical@invite.test",
            "name": "For Mechanical",
            "team_id": other_team.id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )

    listing = client.get("/api/v1/invitations").json()
    emails = {i["email"] for i in listing}
    assert emails == {"for.mechanical@invite.test"}
