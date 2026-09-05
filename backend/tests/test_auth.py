import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import GlobalRole, UserStatus
from app.models.user import User


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter():
    from app.services import auth as auth_service

    auth_service.login_rate_limiter.reset_all()
    yield


def make_user(db_session: Session, **overrides) -> User:
    defaults = dict(
        name="Alice",
        email="alice@example.org",
        password_hash=hash_password("correct-horse-battery-staple"),
        global_role=GlobalRole.USER,
        status=UserStatus.ACTIVE,
    )
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    return user


def test_login_succeeds_with_correct_credentials(client: TestClient, db_session: Session) -> None:
    make_user(db_session)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.org", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "alice@example.org"
    assert "session" in response.cookies
    assert "csrf" in response.cookies


def test_login_rejects_wrong_password_with_generic_message(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session)
    response = client.post(
        "/api/v1/auth/login", json={"email": "alice@example.org", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_rejects_unknown_email_with_same_generic_message(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.org", "password": "whatever"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_inactive_user_cannot_login(client: TestClient, db_session: Session) -> None:
    make_user(db_session, status=UserStatus.INACTIVE)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.org", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 401


def test_me_requires_authentication(client: TestClient) -> None:
    # The `client` fixture logs in as a hidden test-admin by default (so
    # the rest of the suite can exercise authorized endpoints) — log back
    # out to exercise the actual unauthenticated case.
    client.post("/api/v1/auth/logout")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_after_login(client: TestClient, db_session: Session) -> None:
    make_user(db_session)
    client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.org", "password": "correct-horse-battery-staple"},
    )
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.org"


def test_logout_invalidates_session(client: TestClient, db_session: Session) -> None:
    make_user(db_session)
    client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.org", "password": "correct-horse-battery-staple"},
    )
    assert client.get("/api/v1/auth/me").status_code == 200

    csrf_token = client.cookies.get("csrf")
    logout_response = client.post(
        "/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token}
    )
    assert logout_response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_csrf_blocks_mutating_request_without_matching_token(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session)
    client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.org", "password": "correct-horse-battery-staple"},
    )
    # No X-CSRF-Token header sent, even though a session cookie exists.
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403


def test_csrf_allows_mutating_request_with_matching_token(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session)
    client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.org", "password": "correct-horse-battery-staple"},
    )
    csrf_token = client.cookies.get("csrf")
    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert response.status_code == 204


def test_password_reset_flow(client: TestClient, db_session: Session) -> None:
    from app.services import auth as auth_service

    user = make_user(db_session)
    token = auth_service.request_password_reset(db_session, "alice@example.org")
    assert token is not None

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "brand-new-password-123"},
    )
    assert confirm.status_code == 204

    db_session.refresh(user)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.org", "password": "brand-new-password-123"},
    )
    assert login.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.org", "password": "correct-horse-battery-staple"},
    )
    assert old_login.status_code == 401


def test_password_reset_token_is_single_use(client: TestClient, db_session: Session) -> None:
    from app.services import auth as auth_service

    make_user(db_session)
    token = auth_service.request_password_reset(db_session, "alice@example.org")

    first = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "first-new-password-1"},
    )
    assert first.status_code == 204

    second = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "second-new-password-2"},
    )
    assert second.status_code == 400


def test_password_reset_token_expiry_is_enforced(client: TestClient, db_session: Session) -> None:
    from app.core.security import generate_token, hash_token, utc_now
    from app.models.password_reset_token import PasswordResetToken

    user = make_user(db_session)
    token = generate_token()
    db_session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=utc_now() - dt.timedelta(hours=1),
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "does-not-matter-1"},
    )
    assert response.status_code == 400


def test_unknown_email_password_reset_request_still_returns_204(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "nobody@example.org"}
    )
    assert response.status_code == 204


def test_login_rate_limit_blocks_after_repeated_attempts(
    client: TestClient, db_session: Session
) -> None:
    from app.services import auth as auth_service

    make_user(db_session)

    last_status = None
    for _ in range(auth_service._settings.login_rate_limit_attempts + 1):
        last_status = client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.org", "password": "wrong"},
        ).status_code
    assert last_status == 429
