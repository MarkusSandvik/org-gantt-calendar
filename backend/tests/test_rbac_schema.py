import datetime as dt

from sqlalchemy.orm import Session

from app.models.auth_session import AuthSession
from app.models.enums import GlobalRole, InvitationStatus, TeamRole, UserStatus
from app.models.invitation import Invitation
from app.models.password_reset_token import PasswordResetToken
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User


def test_user_has_password_hash_global_role_and_status(db_session: Session) -> None:
    user = User(
        name="Test",
        email="test@example.org",
        password_hash="hashed",
        global_role=GlobalRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    assert user.global_role == GlobalRole.ADMIN
    assert user.status == UserStatus.ACTIVE
    assert user.password_hash == "hashed"
    assert user.last_login_at is None


def test_team_membership_has_team_role_and_unique_constraint(db_session: Session) -> None:
    project = Project(name="P")
    team = Team(project=project, name="Embedded", category="hardware")
    user = User(name="Lead", email="lead@example.org", global_role=GlobalRole.USER)
    db_session.add_all([project, team, user])
    db_session.commit()

    membership = TeamMembership(team_id=team.id, user_id=user.id, team_role=TeamRole.LEAD)
    db_session.add(membership)
    db_session.commit()
    assert membership.team_role == TeamRole.LEAD

    duplicate = TeamMembership(team_id=team.id, user_id=user.id, team_role=TeamRole.MEMBER)
    db_session.add(duplicate)
    try:
        db_session.commit()
        assert False, "expected the unique constraint to reject a duplicate membership"
    except Exception:
        db_session.rollback()


def test_invitation_model_round_trip(db_session: Session) -> None:
    project = Project(name="P")
    team = Team(project=project, name="Mechanical", category="hardware")
    admin = User(name="Admin", email="admin@example.org", global_role=GlobalRole.ADMIN)
    db_session.add_all([project, team, admin])
    db_session.commit()

    invitation = Invitation(
        email="new@example.org",
        name="New Person",
        team_id=team.id,
        target_global_role=GlobalRole.USER,
        target_team_role=TeamRole.MEMBER,
        invited_by_user_id=admin.id,
        token_hash="abc123",
        status=InvitationStatus.PENDING,
        expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=7),
    )
    db_session.add(invitation)
    db_session.commit()

    assert invitation.status == InvitationStatus.PENDING
    assert invitation.team.name == "Mechanical"
    assert invitation.invited_by.name == "Admin"


def test_auth_session_and_password_reset_token_models(db_session: Session) -> None:
    user = User(name="U", email="u@example.org", global_role=GlobalRole.USER)
    db_session.add(user)
    db_session.commit()

    session = AuthSession(
        user_id=user.id,
        token_hash="sesshash",
        expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
    )
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash="resethash",
        expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
    )
    db_session.add_all([session, reset])
    db_session.commit()

    assert session.revoked_at is None
    assert reset.used_at is None
