from fastapi.testclient import TestClient

from tests.conftest import SEED_USER_PASSWORD


def make_payload(seed_basics: dict[str, int], **overrides) -> dict:
    payload = {
        "project_id": seed_basics["project_id"],
        "title": "Pressure Housing Design",
        "description": "Design of the watertight electronics housing.",
        "start_date": "2026-08-05",
        "end_date": "2026-09-20",
        "status": "in_progress",
        "progress_percent": 65,
        "priority": "normal",
        "owner_team_id": seed_basics["team_id"],
        "owner_user_id": seed_basics["user_id"],
        "contributor_user_ids": [seed_basics["other_user_id"]],
        "tag_ids": [seed_basics["tag_id"]],
    }
    payload.update(overrides)
    return payload


def test_create_activity(client: TestClient, seed_basics: dict[str, int], as_user) -> None:
    as_user(client, "alice@example.org", SEED_USER_PASSWORD)
    response = client.post("/api/v1/activities", json=make_payload(seed_basics))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Pressure Housing Design"
    assert body["owner_team"]["id"] == seed_basics["team_id"]
    assert body["owner_user"]["id"] == seed_basics["user_id"]
    assert body["created_by"]["id"] == seed_basics["user_id"]
    assert [c["id"] for c in body["contributors"]] == [seed_basics["other_user_id"]]
    assert [t["id"] for t in body["tags"]] == [seed_basics["tag_id"]]


def test_create_activity_rejects_end_before_start(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/activities",
        json=make_payload(seed_basics, start_date="2026-09-20", end_date="2026-08-05"),
    )
    assert response.status_code == 422


def test_create_activity_rejects_unknown_team(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/activities", json=make_payload(seed_basics, owner_team_id=9999)
    )
    assert response.status_code == 404


def test_create_activity_rejects_out_of_range_progress(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/activities", json=make_payload(seed_basics, progress_percent=150)
    )
    assert response.status_code == 422


def test_list_and_get_activity(client: TestClient, seed_basics: dict[str, int]) -> None:
    created = client.post("/api/v1/activities", json=make_payload(seed_basics)).json()

    listed = client.get(
        "/api/v1/activities", params={"project_id": seed_basics["project_id"]}
    ).json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]

    fetched = client.get(f"/api/v1/activities/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Pressure Housing Design"


def test_list_activity_filters(client: TestClient, seed_basics: dict[str, int]) -> None:
    client.post(
        "/api/v1/activities",
        json=make_payload(seed_basics, title="Delayed thing", status="delayed"),
    )
    client.post(
        "/api/v1/activities",
        json=make_payload(seed_basics, title="On track thing", status="in_progress"),
    )

    delayed_only = client.get(
        "/api/v1/activities", params={"status": "delayed"}
    ).json()
    assert len(delayed_only) == 1
    assert delayed_only[0]["title"] == "Delayed thing"

    search = client.get("/api/v1/activities", params={"q": "on track"}).json()
    assert len(search) == 1
    assert search[0]["title"] == "On track thing"


def test_list_activity_filter_by_tag(client: TestClient, seed_basics: dict[str, int]) -> None:
    tagged = client.post("/api/v1/activities", json=make_payload(seed_basics)).json()
    client.post(
        "/api/v1/activities",
        json=make_payload(seed_basics, title="Untagged thing", tag_ids=[]),
    )

    result = client.get(
        "/api/v1/activities", params={"tag_id": seed_basics["tag_id"]}
    ).json()
    assert [a["id"] for a in result] == [tagged["id"]]


def test_list_activity_filter_by_contributor(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    with_contributor = client.post(
        "/api/v1/activities", json=make_payload(seed_basics)
    ).json()
    client.post(
        "/api/v1/activities",
        json=make_payload(seed_basics, title="No contributors", contributor_user_ids=[]),
    )

    result = client.get(
        "/api/v1/activities", params={"contributor_user_id": seed_basics["other_user_id"]}
    ).json()
    assert [a["id"] for a in result] == [with_contributor["id"]]


def test_list_activity_filter_by_date_range(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    # Default fixture activity runs 2026-08-05 to 2026-09-20.
    early = client.post(
        "/api/v1/activities",
        json=make_payload(
            seed_basics, title="Early thing", start_date="2026-01-01", end_date="2026-01-31"
        ),
    ).json()
    default = client.post("/api/v1/activities", json=make_payload(seed_basics)).json()

    in_range = client.get(
        "/api/v1/activities",
        params={"date_from": "2026-09-01", "date_to": "2026-09-30"},
    ).json()
    assert [a["id"] for a in in_range] == [default["id"]]

    early_range = client.get(
        "/api/v1/activities",
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
    ).json()
    assert [a["id"] for a in early_range] == [early["id"]]


def test_update_activity_partial(client: TestClient, seed_basics: dict[str, int]) -> None:
    created = client.post("/api/v1/activities", json=make_payload(seed_basics)).json()

    response = client.patch(
        f"/api/v1/activities/{created['id']}",
        json={"progress_percent": 80, "status": "completed"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["progress_percent"] == 80
    assert body["status"] == "completed"
    # Untouched fields survive the partial update.
    assert body["title"] == "Pressure Housing Design"
    assert [c["id"] for c in body["contributors"]] == [seed_basics["other_user_id"]]


def test_update_activity_can_clear_contributors(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    created = client.post("/api/v1/activities", json=make_payload(seed_basics)).json()

    response = client.patch(
        f"/api/v1/activities/{created['id']}", json={"contributor_user_ids": []}
    )
    assert response.status_code == 200
    assert response.json()["contributors"] == []


def test_update_activity_rejects_date_regression(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    created = client.post("/api/v1/activities", json=make_payload(seed_basics)).json()

    response = client.patch(
        f"/api/v1/activities/{created['id']}", json={"end_date": "2026-01-01"}
    )
    assert response.status_code == 422


def test_delete_activity(client: TestClient, seed_basics: dict[str, int]) -> None:
    created = client.post("/api/v1/activities", json=make_payload(seed_basics)).json()

    response = client.delete(f"/api/v1/activities/{created['id']}")
    assert response.status_code == 204

    assert client.get(f"/api/v1/activities/{created['id']}").status_code == 404


def test_delete_activity_blocked_by_dependency(
    client: TestClient, db_session, seed_basics: dict[str, int]
) -> None:
    from app.models.dependency import Dependency
    from app.models.enums import DependencyType, SchedulableType

    first = client.post("/api/v1/activities", json=make_payload(seed_basics)).json()
    second = client.post(
        "/api/v1/activities",
        json=make_payload(seed_basics, title="System Integration"),
    ).json()

    db_session.add(
        Dependency(
            predecessor_type=SchedulableType.ACTIVITY,
            predecessor_id=first["id"],
            successor_type=SchedulableType.ACTIVITY,
            successor_id=second["id"],
            dependency_type=DependencyType.FINISH_TO_START,
        )
    )
    db_session.commit()

    response = client.delete(f"/api/v1/activities/{first['id']}")
    assert response.status_code == 409
