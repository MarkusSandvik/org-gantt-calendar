from fastapi.testclient import TestClient


def make_activity(client: TestClient, seed_basics: dict[str, int], **overrides) -> dict:
    payload = {
        "project_id": seed_basics["project_id"],
        "title": "Pool Test",
        "start_date": "2026-10-22",
        "end_date": "2026-10-24",
        "status": "not_started",
        "contributor_user_ids": [],
        "tag_ids": [],
    }
    payload.update(overrides)
    return client.post("/api/v1/activities", json=payload).json()


def test_create_and_list_activity_comment(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics)

    response = client.post(
        f"/api/v1/activities/{activity['id']}/comments",
        json={"body": "PCB sent to production."},
        headers={"X-User-Id": str(seed_basics["user_id"])},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["body"] == "PCB sent to production."
    assert body["author"]["id"] == seed_basics["user_id"]
    assert body["status_change_from"] is None

    listed = client.get(f"/api/v1/activities/{activity['id']}/comments").json()
    assert len(listed) == 1
    assert listed[0]["body"] == "PCB sent to production."


def test_comments_ordered_chronologically(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics)
    client.post(f"/api/v1/activities/{activity['id']}/comments", json={"body": "First"})
    client.post(f"/api/v1/activities/{activity['id']}/comments", json={"body": "Second"})

    listed = client.get(f"/api/v1/activities/{activity['id']}/comments").json()
    assert [c["body"] for c in listed] == ["First", "Second"]


def test_comment_requires_nonempty_body(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics)
    response = client.post(f"/api/v1/activities/{activity['id']}/comments", json={"body": ""})
    assert response.status_code == 422


def test_comment_on_unknown_activity_404(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post("/api/v1/activities/9999/comments", json={"body": "Hi"})
    assert response.status_code == 404


def test_milestone_comments(client: TestClient, db_session, seed_basics: dict[str, int]) -> None:
    import datetime as dt

    from app.models.milestone import Milestone

    milestone = Milestone(
        project_id=seed_basics["project_id"],
        title="Architecture Freeze",
        date=dt.date(2026, 9, 18),
    )
    db_session.add(milestone)
    db_session.commit()

    response = client.post(
        f"/api/v1/milestones/{milestone.id}/comments",
        json={"body": "Supplier confirmed production start."},
    )
    assert response.status_code == 201, response.text

    listed = client.get(f"/api/v1/milestones/{milestone.id}/comments").json()
    assert len(listed) == 1
    assert listed[0]["body"] == "Supplier confirmed production start."


def test_status_change_creates_auto_comment_with_reason(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics, status="not_started")

    response = client.patch(
        f"/api/v1/activities/{activity['id']}",
        json={"status": "delayed", "reason": "Supplier delivery slipped a week"},
    )
    assert response.status_code == 200

    comments = client.get(f"/api/v1/activities/{activity['id']}/comments").json()
    status_comments = [c for c in comments if c["status_change_from"] is not None]
    assert len(status_comments) == 1
    assert status_comments[0]["status_change_from"] == "not_started"
    assert status_comments[0]["status_change_to"] == "delayed"
    assert status_comments[0]["body"] == "Supplier delivery slipped a week"


def test_status_unchanged_creates_no_status_comment(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics, status="in_progress")

    client.patch(f"/api/v1/activities/{activity['id']}", json={"status": "in_progress"})

    comments = client.get(f"/api/v1/activities/{activity['id']}/comments").json()
    assert comments == []
