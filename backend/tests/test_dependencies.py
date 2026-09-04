import datetime as dt

from fastapi.testclient import TestClient


def make_activity(client: TestClient, seed_basics: dict[str, int], title: str) -> dict:
    return client.post(
        "/api/v1/activities",
        json={
            "project_id": seed_basics["project_id"],
            "title": title,
            "start_date": "2026-08-01",
            "end_date": "2026-08-10",
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    ).json()


def test_create_dependency_between_activities(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a = make_activity(client, seed_basics, "PCB Design")
    b = make_activity(client, seed_basics, "PCB Assembly")

    response = client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a["id"],
            "successor_type": "activity",
            "successor_id": b["id"],
            "lag_days": 2,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["predecessor_label"] == "PCB Design"
    assert body["successor_label"] == "PCB Assembly"
    assert body["lag_days"] == 2
    assert body["dependency_type"] == "finish_to_start"


def test_create_dependency_rejects_self_loop(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a = make_activity(client, seed_basics, "Solo thing")
    response = client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a["id"],
            "successor_type": "activity",
            "successor_id": a["id"],
        },
    )
    assert response.status_code == 422


def test_create_dependency_rejects_unknown_endpoint(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a = make_activity(client, seed_basics, "Real thing")
    response = client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a["id"],
            "successor_type": "activity",
            "successor_id": 9999,
        },
    )
    assert response.status_code == 404


def test_create_dependency_rejects_duplicate(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a = make_activity(client, seed_basics, "A")
    b = make_activity(client, seed_basics, "B")
    payload = {
        "predecessor_type": "activity",
        "predecessor_id": a["id"],
        "successor_type": "activity",
        "successor_id": b["id"],
    }
    assert client.post("/api/v1/dependencies", json=payload).status_code == 201
    response = client.post("/api/v1/dependencies", json=payload)
    assert response.status_code == 409


def test_create_dependency_rejects_cycle(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a = make_activity(client, seed_basics, "A")
    b = make_activity(client, seed_basics, "B")
    c = make_activity(client, seed_basics, "C")

    def dep(pred: dict, succ: dict) -> dict:
        return {
            "predecessor_type": "activity",
            "predecessor_id": pred["id"],
            "successor_type": "activity",
            "successor_id": succ["id"],
        }

    assert client.post("/api/v1/dependencies", json=dep(a, b)).status_code == 201
    assert client.post("/api/v1/dependencies", json=dep(b, c)).status_code == 201

    # C -> A would close the loop A -> B -> C -> A.
    response = client.post("/api/v1/dependencies", json=dep(c, a))
    assert response.status_code == 409
    assert "cycle" in response.json()["detail"].lower()


def test_dependency_between_activity_and_milestone(
    client: TestClient, db_session, seed_basics: dict[str, int]
) -> None:
    from app.models.milestone import Milestone

    milestone = Milestone(
        project_id=seed_basics["project_id"],
        title="Architecture Freeze",
        date=dt.date(2026, 9, 1),
    )
    db_session.add(milestone)
    db_session.commit()

    activity = make_activity(client, seed_basics, "Design work")

    response = client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": activity["id"],
            "successor_type": "milestone",
            "successor_id": milestone.id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["successor_type"] == "milestone"
    assert body["successor_label"] == "Architecture Freeze"


def test_list_dependencies(client: TestClient, seed_basics: dict[str, int]) -> None:
    a = make_activity(client, seed_basics, "A")
    b = make_activity(client, seed_basics, "B")
    client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a["id"],
            "successor_type": "activity",
            "successor_id": b["id"],
        },
    )

    result = client.get("/api/v1/dependencies").json()
    assert len(result) == 1
    assert result[0]["predecessor_label"] == "A"
    assert result[0]["successor_label"] == "B"


def test_delete_dependency(client: TestClient, seed_basics: dict[str, int]) -> None:
    a = make_activity(client, seed_basics, "A")
    b = make_activity(client, seed_basics, "B")
    created = client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a["id"],
            "successor_type": "activity",
            "successor_id": b["id"],
        },
    ).json()

    response = client.delete(f"/api/v1/dependencies/{created['id']}")
    assert response.status_code == 204
    assert client.get("/api/v1/dependencies").json() == []
