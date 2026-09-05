import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter():
    """Every test that uses `client` logs in during fixture setup, all as
    the same test-admin identity from the same synthetic test-client IP —
    without this, the login rate limiter (correctly) starts blocking that
    after a handful of tests, since it can't distinguish 150 unrelated
    tests from one client hammering the login endpoint."""
    from app.services import auth as auth_service

    auth_service.login_rate_limiter.reset_all()
    yield


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()


TEST_ADMIN_EMAIL = "test-admin@example.org"
TEST_ADMIN_PASSWORD = "test-admin-password-123"
SEED_USER_PASSWORD = "seed-user-password-123"


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """A TestClient that's already logged in as a hidden Admin user, with
    the CSRF header pre-set for every request — so the ~100 tests written
    before real authentication existed keep exercising authorization as
    an Admin (the least restrictive role) without every call site needing
    its own login/CSRF dance. Tests that specifically need a Lead or
    Member identity log in separately via the `as_user` fixture."""
    from app.core.security import hash_password
    from app.models.enums import GlobalRole, UserStatus
    from app.models.user import User

    db_session.add(
        User(
            name="Test Admin",
            email=TEST_ADMIN_EMAIL,
            password_hash=hash_password(TEST_ADMIN_PASSWORD),
            global_role=GlobalRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
    )
    db_session.commit()

    with TestClient(app) as test_client:
        test_client.post(
            "/api/v1/auth/login",
            json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
        )
        test_client.headers["X-CSRF-Token"] = test_client.cookies.get("csrf", "")
        yield test_client


@pytest.fixture()
def as_user():
    """Logs the given TestClient in as `email`/`password`, replacing
    whatever identity it was previously authenticated as — for tests that
    need to act as a specific Lead or Member rather than the default
    Admin the `client` fixture logs in as."""

    def _as_user(test_client: TestClient, email: str, password: str) -> None:
        test_client.post("/api/v1/auth/logout")
        test_client.post("/api/v1/auth/login", json={"email": email, "password": password})
        test_client.headers["X-CSRF-Token"] = test_client.cookies.get("csrf", "")

    return _as_user


@pytest.fixture()
def seed_basics(db_session: Session) -> dict[str, int]:
    """Minimal reference data (project, team, user, tag) that most entity
    tests need to exist before they can create an activity."""
    from app.core.security import hash_password
    from app.models.enums import GlobalRole, TeamCategory, UserStatus
    from app.models.project import Project
    from app.models.tag import Tag
    from app.models.team import Team
    from app.models.user import User

    project = Project(name="Test Project")
    team = Team(project=project, name="Mechanical", category=TeamCategory.HARDWARE)
    user = User(
        name="Alice",
        email="alice@example.org",
        password_hash=hash_password(SEED_USER_PASSWORD),
        global_role=GlobalRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    other_user = User(
        name="Bob",
        email="bob@example.org",
        password_hash=hash_password(SEED_USER_PASSWORD),
        global_role=GlobalRole.USER,
        status=UserStatus.ACTIVE,
    )
    tag = Tag(project=project, name="Testing")

    db_session.add_all([project, team, user, other_user, tag])
    db_session.commit()

    return {
        "project_id": project.id,
        "team_id": team.id,
        "user_id": user.id,
        "other_user_id": other_user.id,
        "tag_id": tag.id,
    }
