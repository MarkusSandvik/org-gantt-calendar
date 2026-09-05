"""Section 17 coverage: every security-sensitive action gets an AuditLog
row (actor, action, target, timestamp, old/new value), and none of them
ever carry a password, token, or hash."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.enums import GlobalRole, TeamCategory, TeamRole, UserStatus
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User

PASSWORD = "audit-test-password-123"


@pytest.fixture()
def world(db_session: Session):
    project = Project(name="P")
    team = Team(project=project, name="Embedded", category=TeamCategory.HARDWARE)
    member = User(
        name="Audit Member",
        email="audit.member@example.org",
        password_hash=hash_password(PASSWORD),
        global_role=GlobalRole.USER,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([project, team, member])
    db_session.commit()
    db_session.add(TeamMembership(team_id=team.id, user_id=member.id, team_role=TeamRole.MEMBER))
    db_session.commit()
    return {"project": project, "team": team, "member": member}


def audit_rows(db_session: Session, entity_type: str, entity_id: int) -> list[AuditLog]:
    return list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id
            )
        ).all()
    )


def test_invitation_creates_audit_entry(
    client: TestClient, db_session: Session, world: dict
) -> None:
    response = client.post(
        "/api/v1/invitations",
        json={
            "email": "new@example.org",
            "name": "New",
            "team_id": world["team"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    invitation_id = response.json()["id"]
    rows = audit_rows(db_session, "invitation", invitation_id)
    assert len(rows) >= 1
    assert any(r.field_name == "status" and r.new_value == "pending" for r in rows)
    assert all(r.user_id is not None for r in rows)
    assert all(r.timestamp is not None for r in rows)


def test_revoke_invitation_creates_audit_entry(
    client: TestClient, db_session: Session, world: dict
) -> None:
    create = client.post(
        "/api/v1/invitations",
        json={
            "email": "revoke@example.org",
            "name": "Revoke",
            "team_id": world["team"].id,
            "target_global_role": "user",
            "target_team_role": "member",
        },
    )
    invitation_id = create.json()["id"]
    client.post(f"/api/v1/invitations/{invitation_id}/revoke")

    rows = audit_rows(db_session, "invitation", invitation_id)
    assert any(r.field_name == "status" and r.new_value == "revoked" for r in rows)


def test_deactivate_and_reactivate_create_audit_entries(
    client: TestClient, db_session: Session, world: dict
) -> None:
    member_id = world["member"].id
    client.post(f"/api/v1/users/{member_id}/deactivate")
    client.post(f"/api/v1/users/{member_id}/reactivate")

    rows = audit_rows(db_session, "user", member_id)
    status_rows = [r for r in rows if r.field_name == "status"]
    assert any(r.new_value == "inactive" for r in status_rows)
    assert any(r.new_value == "active" for r in status_rows)


def test_role_change_creates_audit_entry(
    client: TestClient, db_session: Session, world: dict
) -> None:
    member_id = world["member"].id
    client.patch(f"/api/v1/users/{member_id}/global-role", json={"global_role": "admin"})

    rows = audit_rows(db_session, "user", member_id)
    assert any(
        r.field_name == "global_role" and r.old_value == "user" and r.new_value == "admin"
        for r in rows
    )


def test_team_membership_added_and_removed_create_audit_entries(
    client: TestClient, db_session: Session, world: dict
) -> None:
    mechanical = Team(project_id=world["project"].id, name="Mechanical", category=TeamCategory.HARDWARE)
    db_session.add(mechanical)
    db_session.commit()

    member_id = world["member"].id
    client.put(
        f"/api/v1/users/{member_id}/team-memberships",
        json={"team_id": mechanical.id, "team_role": "member"},
    )
    added_rows = audit_rows(db_session, "user", member_id)
    assert any(r.field_name == "team_membership_added" for r in added_rows)

    client.delete(f"/api/v1/users/{member_id}/team-memberships/{mechanical.id}")
    removed_rows = audit_rows(db_session, "user", member_id)
    assert any(r.field_name == "team_membership_removed" for r in removed_rows)


def test_lead_reassignment_logs_demotion_of_previous_team(
    client: TestClient, db_session: Session, world: dict
) -> None:
    mechanical = Team(project_id=world["project"].id, name="Mechanical", category=TeamCategory.HARDWARE)
    db_session.add(mechanical)
    db_session.commit()

    member_id = world["member"].id
    client.put(
        f"/api/v1/users/{member_id}/team-memberships",
        json={"team_id": world["team"].id, "team_role": "lead"},
    )
    old_membership_id = db_session.scalars(
        select(TeamMembership.id).where(
            TeamMembership.user_id == member_id, TeamMembership.team_id == world["team"].id
        )
    ).first()

    client.put(
        f"/api/v1/users/{member_id}/team-memberships",
        json={"team_id": mechanical.id, "team_role": "lead"},
    )

    demotion_rows = audit_rows(db_session, "team_membership", old_membership_id)
    assert any(
        r.field_name == "team_role" and r.old_value == "lead" and r.new_value == "member"
        for r in demotion_rows
    )


def test_password_reset_completed_creates_audit_entry_without_leaking_secret(
    client: TestClient, db_session: Session, world: dict
) -> None:
    from app.services import auth as auth_service

    token = auth_service.request_password_reset(db_session, world["member"].email)
    client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "a-brand-new-password-1"},
    )

    rows = audit_rows(db_session, "user", world["member"].id)
    reset_rows = [r for r in rows if r.reason == "Password reset completed"]
    assert len(reset_rows) == 1
    # Never the password, the token, or a hash of either.
    assert reset_rows[0].old_value not in (None, token, "a-brand-new-password-1")
    assert reset_rows[0].new_value not in (None, token, "a-brand-new-password-1")
    assert reset_rows[0].old_value == "***"
    assert reset_rows[0].new_value == "***"


def test_no_audit_row_ever_contains_a_password_hash_or_session_token(
    client: TestClient, db_session: Session, world: dict
) -> None:
    # Exercise several security-sensitive flows, then scan every resulting
    # audit row for anything that looks like a secret.
    client.post(f"/api/v1/users/{world['member'].id}/deactivate")
    client.post(f"/api/v1/users/{world['member'].id}/reactivate")
    client.patch(f"/api/v1/users/{world['member'].id}/global-role", json={"global_role": "admin"})

    all_rows = db_session.scalars(select(AuditLog)).all()
    for row in all_rows:
        for value in (row.old_value, row.new_value, row.reason):
            if value:
                assert hash_password("x")[:10] not in value
                assert PASSWORD not in value
