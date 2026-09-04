import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.db.base import Base
from app.db.session import get_db
from app.main import app


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


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seed_basics(db_session: Session) -> dict[str, int]:
    """Minimal reference data (project, team, user, tag) that most entity
    tests need to exist before they can create an activity."""
    from app.models.enums import TeamCategory, UserRole
    from app.models.project import Project
    from app.models.tag import Tag
    from app.models.team import Team
    from app.models.user import User

    project = Project(name="Test Project")
    team = Team(project=project, name="Mechanical", category=TeamCategory.HARDWARE)
    user = User(name="Alice", email="alice@example.org", role=UserRole.ADMIN)
    other_user = User(name="Bob", email="bob@example.org", role=UserRole.EDITOR)
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
