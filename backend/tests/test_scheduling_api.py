import datetime as dt

from fastapi.testclient import TestClient


def make_activity(
    client: TestClient, seed_basics: dict[str, int], title: str, start: str, end: str
) -> dict:
    return client.post(
        "/api/v1/activities",
        json={
            "project_id": seed_basics["project_id"],
            "title": title,
            "start_date": start,
            "end_date": end,
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    ).json()


def make_dependency(client: TestClient, pred: dict, succ: dict, lag_days: int = 0) -> dict:
    return client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": pred["id"],
            "successor_type": "activity",
            "successor_id": succ["id"],
            "lag_days": lag_days,
        },
    ).json()


def test_preview_does_not_persist_changes(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a = make_activity(client, seed_basics, "A", "2026-01-01", "2026-01-10")
    b = make_activity(client, seed_basics, "B", "2026-01-11", "2026-01-20")
    make_dependency(client, a, b)

    response = client.post(
        "/api/v1/scheduling/preview",
        json={
            "entity_type": "activity",
            "entity_id": a["id"],
            "new_start_date": "2026-01-01",
            "new_end_date": "2026-01-15",
        },
    )
    assert response.status_code == 200, response.text
    changes = response.json()
    ids_changed = {c["entity_id"] for c in changes}
    assert a["id"] in ids_changed and b["id"] in ids_changed

    # Nothing should actually be written.
    b_after = client.get(f"/api/v1/activities/{b['id']}").json()
    assert b_after["start_date"] == "2026-01-11"
    assert b_after["end_date"] == "2026-01-20"


def test_apply_persists_and_writes_shared_audit_group(
    client: TestClient, db_session, seed_basics: dict[str, int]
) -> None:
    from app.models.audit_log import AuditLog

    a = make_activity(client, seed_basics, "A", "2026-01-01", "2026-01-10")
    b = make_activity(client, seed_basics, "B", "2026-01-11", "2026-01-20")
    make_dependency(client, a, b)

    response = client.post(
        "/api/v1/scheduling/apply",
        json={
            "entity_type": "activity",
            "entity_id": a["id"],
            "new_start_date": "2026-01-01",
            "new_end_date": "2026-01-15",
            "reason": "Supplier delay",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["change_group_id"]
    assert len(body["changes"]) == 2

    a_after = client.get(f"/api/v1/activities/{a['id']}").json()
    b_after = client.get(f"/api/v1/activities/{b['id']}").json()
    assert a_after["end_date"] == "2026-01-15"
    assert b_after["start_date"] == "2026-01-15"
    assert b_after["end_date"] == "2026-01-24"  # 10-day duration preserved

    logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.change_group_id == body["change_group_id"])
        .all()
    )
    assert len(logs) == 4  # start+end for both A and B
    assert all(log.reason == "Supplier delay" for log in logs)


def test_apply_with_no_dependents_updates_only_that_node(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a = make_activity(client, seed_basics, "Solo", "2026-01-01", "2026-01-10")

    response = client.post(
        "/api/v1/scheduling/apply",
        json={
            "entity_type": "activity",
            "entity_id": a["id"],
            "new_start_date": "2026-01-05",
            "new_end_date": "2026-01-15",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["changes"]) == 1
    assert body["changes"][0]["entity_id"] == a["id"]


def test_undo_reverts_dates_and_is_itself_audited(
    client: TestClient, db_session, seed_basics: dict[str, int]
) -> None:
    from app.models.audit_log import AuditLog

    a = make_activity(client, seed_basics, "A", "2026-01-01", "2026-01-10")
    b = make_activity(client, seed_basics, "B", "2026-01-11", "2026-01-20")
    make_dependency(client, a, b)

    apply_response = client.post(
        "/api/v1/scheduling/apply",
        json={
            "entity_type": "activity",
            "entity_id": a["id"],
            "new_start_date": "2026-01-01",
            "new_end_date": "2026-01-15",
        },
    ).json()
    group_id = apply_response["change_group_id"]

    undo_response = client.post(
        "/api/v1/scheduling/undo", json={"change_group_id": group_id}
    )
    assert undo_response.status_code == 200, undo_response.text

    a_after = client.get(f"/api/v1/activities/{a['id']}").json()
    b_after = client.get(f"/api/v1/activities/{b['id']}").json()
    assert a_after["start_date"] == "2026-01-01"
    assert a_after["end_date"] == "2026-01-10"
    assert b_after["start_date"] == "2026-01-11"
    assert b_after["end_date"] == "2026-01-20"

    # The undo itself must be audited, under a *different* change_group_id.
    undo_logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.reason == "Undo scheduling change")
        .all()
    )
    assert len(undo_logs) == 4
    assert {log.change_group_id for log in undo_logs} != {group_id}


def test_undo_unknown_group_404(client: TestClient, seed_basics: dict[str, int]) -> None:
    response = client.post(
        "/api/v1/scheduling/undo", json={"change_group_id": "does-not-exist"}
    )
    assert response.status_code == 404


def test_preview_unknown_entity_404(client: TestClient, seed_basics: dict[str, int]) -> None:
    response = client.post(
        "/api/v1/scheduling/preview",
        json={
            "entity_type": "activity",
            "entity_id": 9999,
            "new_start_date": "2026-01-01",
            "new_end_date": "2026-01-10",
        },
    )
    assert response.status_code == 404


def test_preview_rejects_end_before_start(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a = make_activity(client, seed_basics, "A", "2026-01-01", "2026-01-10")
    response = client.post(
        "/api/v1/scheduling/preview",
        json={
            "entity_type": "activity",
            "entity_id": a["id"],
            "new_start_date": "2026-01-10",
            "new_end_date": "2026-01-01",
        },
    )
    assert response.status_code == 422


def test_scheduling_milestone_change(
    client: TestClient, db_session, seed_basics: dict[str, int]
) -> None:
    from app.models.milestone import Milestone

    milestone = Milestone(
        project_id=seed_basics["project_id"],
        title="Architecture Freeze",
        date=dt.date(2026, 2, 1),
    )
    db_session.add(milestone)
    db_session.commit()

    a = make_activity(client, seed_basics, "Follow-up work", "2026-02-02", "2026-02-10")
    client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "milestone",
            "predecessor_id": milestone.id,
            "successor_type": "activity",
            "successor_id": a["id"],
        },
    )

    response = client.post(
        "/api/v1/scheduling/apply",
        json={
            "entity_type": "milestone",
            "entity_id": milestone.id,
            "new_start_date": "2026-02-08",
            "new_end_date": "2026-02-08",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["changes"]) == 2

    a_after = client.get(f"/api/v1/activities/{a['id']}").json()
    assert a_after["start_date"] == "2026-02-08"
