from fastapi.testclient import TestClient


def make_payload(seed_basics: dict[str, int], **overrides) -> dict:
    payload = {
        "project_id": seed_basics["project_id"],
        "title": "Architecture Freeze",
        "description": "All major interfaces locked.",
        "date": "2026-09-18",
        "status": "on_track",
        "team_id": seed_basics["team_id"],
        "owner_user_id": seed_basics["user_id"],
        "tag_ids": [seed_basics["tag_id"]],
    }
    payload.update(overrides)
    return payload


def test_create_milestone(client: TestClient, seed_basics: dict[str, int]) -> None:
    response = client.post("/api/v1/milestones", json=make_payload(seed_basics))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Architecture Freeze"
    assert body["team"]["id"] == seed_basics["team_id"]
    assert body["owner_user"]["id"] == seed_basics["user_id"]
    assert [t["id"] for t in body["tags"]] == [seed_basics["tag_id"]]


def test_create_milestone_rejects_unknown_team(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/milestones", json=make_payload(seed_basics, team_id=9999)
    )
    assert response.status_code == 404


def test_list_milestones_filter_by_status_and_tag(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/milestones",
        json=make_payload(seed_basics, title="On track thing", status="on_track"),
    )
    client.post(
        "/api/v1/milestones",
        json=make_payload(seed_basics, title="At risk thing", status="at_risk"),
    )

    at_risk = client.get("/api/v1/milestones", params={"status": "at_risk"}).json()
    assert len(at_risk) == 1
    assert at_risk[0]["title"] == "At risk thing"

    tagged = client.get(
        "/api/v1/milestones", params={"tag_id": seed_basics["tag_id"]}
    ).json()
    assert len(tagged) == 2


def test_update_milestone_partial(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    created = client.post(
        "/api/v1/milestones", json=make_payload(seed_basics)
    ).json()

    response = client.patch(
        f"/api/v1/milestones/{created['id']}", json={"status": "completed"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["title"] == "Architecture Freeze"  # untouched
    assert [t["id"] for t in body["tags"]] == [seed_basics["tag_id"]]  # untouched


def test_update_milestone_can_clear_tags(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    created = client.post(
        "/api/v1/milestones", json=make_payload(seed_basics)
    ).json()

    response = client.patch(f"/api/v1/milestones/{created['id']}", json={"tag_ids": []})
    assert response.status_code == 200
    assert response.json()["tags"] == []


def test_delete_milestone(client: TestClient, seed_basics: dict[str, int]) -> None:
    created = client.post(
        "/api/v1/milestones", json=make_payload(seed_basics)
    ).json()

    response = client.delete(f"/api/v1/milestones/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/milestones/{created['id']}").status_code == 404


def test_delete_milestone_blocked_by_dependency(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    milestone = client.post(
        "/api/v1/milestones", json=make_payload(seed_basics)
    ).json()
    activity = client.post(
        "/api/v1/activities",
        json={
            "project_id": seed_basics["project_id"],
            "title": "Prep work",
            "start_date": "2026-09-01",
            "end_date": "2026-09-17",
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    ).json()

    client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": activity["id"],
            "successor_type": "milestone",
            "successor_id": milestone["id"],
        },
    )

    response = client.delete(f"/api/v1/milestones/{milestone['id']}")
    assert response.status_code == 409


def test_list_milestones_filter_by_owner_user(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/milestones",
        json=make_payload(seed_basics, title="Alice's milestone", owner_user_id=seed_basics["user_id"]),
    )
    client.post(
        "/api/v1/milestones",
        json=make_payload(
            seed_basics, title="Bob's milestone", owner_user_id=seed_basics["other_user_id"]
        ),
    )

    mine = client.get(
        "/api/v1/milestones", params={"owner_user_id": seed_basics["user_id"]}
    ).json()
    assert [m["title"] for m in mine] == ["Alice's milestone"]
