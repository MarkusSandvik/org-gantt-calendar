from fastapi.testclient import TestClient


def make_activity(client: TestClient, seed_basics: dict[str, int], **overrides) -> dict:
    payload = {
        "project_id": seed_basics["project_id"],
        "title": "PCB Design",
        "start_date": "2026-08-10",
        "end_date": "2026-09-04",
        "status": "in_progress",
        "priority": "normal",
        "contributor_user_ids": [],
        "tag_ids": [],
    }
    payload.update(overrides)
    return client.post("/api/v1/activities", json=payload).json()


def test_update_activity_writes_audit_entries(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics)

    response = client.patch(
        f"/api/v1/activities/{activity['id']}",
        json={
            "priority": "high",
            "end_date": "2026-09-10",
            "reason": "Scope grew slightly",
        },
    )
    assert response.status_code == 200

    logs = client.get(
        "/api/v1/audit-log", params={"entity_type": "activity", "entity_id": activity["id"]}
    ).json()
    fields_changed = {log["field_name"] for log in logs}
    assert fields_changed == {"priority", "end_date"}
    assert all(log["reason"] == "Scope grew slightly" for log in logs)
    # Same edit -> same change_group_id, so it reads as one event.
    assert len({log["change_group_id"] for log in logs}) == 1

    priority_log = next(log for log in logs if log["field_name"] == "priority")
    assert priority_log["old_value"] == "normal"
    assert priority_log["new_value"] == "high"


def test_update_activity_with_no_tracked_field_changes_writes_nothing(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics)

    # Re-submitting the same priority is a no-op for audit purposes.
    client.patch(f"/api/v1/activities/{activity['id']}", json={"priority": "normal"})

    logs = client.get(
        "/api/v1/audit-log", params={"entity_type": "activity", "entity_id": activity["id"]}
    ).json()
    assert logs == []


def test_status_change_does_not_appear_in_audit_log(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics, status="not_started")

    client.patch(f"/api/v1/activities/{activity['id']}", json={"status": "delayed"})

    logs = client.get(
        "/api/v1/audit-log", params={"entity_type": "activity", "entity_id": activity["id"]}
    ).json()
    assert all(log["field_name"] != "status" for log in logs)


def test_update_milestone_writes_audit_entries(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    created = client.post(
        "/api/v1/milestones",
        json={
            "project_id": seed_basics["project_id"],
            "title": "Architecture Freeze",
            "date": "2026-09-18",
            "status": "on_track",
            "tag_ids": [],
        },
    ).json()

    client.patch(
        f"/api/v1/milestones/{created['id']}",
        json={"date": "2026-09-25", "reason": "Waiting on one more review"},
    )

    logs = client.get(
        "/api/v1/audit-log", params={"entity_type": "milestone", "entity_id": created["id"]}
    ).json()
    assert len(logs) == 1
    assert logs[0]["field_name"] == "date"
    assert logs[0]["old_value"] == "2026-09-18"
    assert logs[0]["new_value"] == "2026-09-25"
    assert logs[0]["reason"] == "Waiting on one more review"


def test_audit_log_filters_by_entity(client: TestClient, seed_basics: dict[str, int]) -> None:
    a = make_activity(client, seed_basics, title="A")
    b = make_activity(client, seed_basics, title="B")
    client.patch(f"/api/v1/activities/{a['id']}", json={"priority": "critical"})
    client.patch(f"/api/v1/activities/{b['id']}", json={"priority": "low"})

    logs_a = client.get(
        "/api/v1/audit-log", params={"entity_type": "activity", "entity_id": a["id"]}
    ).json()
    assert len(logs_a) == 1
    assert logs_a[0]["new_value"] == "critical"
