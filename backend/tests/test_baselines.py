from fastapi.testclient import TestClient


def make_activity(client: TestClient, seed_basics: dict[str, int], **overrides) -> dict:
    payload = {
        "project_id": seed_basics["project_id"],
        "title": "PCB Design",
        "start_date": "2026-08-10",
        "end_date": "2026-09-04",
        "contributor_user_ids": [],
        "tag_ids": [],
    }
    payload.update(overrides)
    return client.post("/api/v1/activities", json=payload).json()


def create_baseline(client: TestClient, project_id: int, **overrides) -> dict:
    payload = {"name": "Kickoff baseline", "note": None}
    payload.update(overrides)
    response = client.post(
        "/api/v1/baselines", params={"project_id": project_id}, json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_baseline_snapshots_current_dates(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics)
    baseline = create_baseline(client, seed_basics["project_id"])
    assert baseline["name"] == "Kickoff baseline"
    assert baseline["created_by"]["id"]

    comparison = client.get(f"/api/v1/baselines/{baseline['id']}/comparison").json()
    item = next(i for i in comparison["items"] if i["entity_id"] == activity["id"])
    assert item["baseline_start"] == "2026-08-10"
    assert item["baseline_end"] == "2026-09-04"
    assert item["delta_start_days"] == 0
    assert item["delta_end_days"] == 0


def test_multiple_baselines_coexist_without_overwriting(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics)
    early_baseline = create_baseline(client, seed_basics["project_id"], name="Early")

    client.patch(f"/api/v1/activities/{activity['id']}", json={"end_date": "2026-09-14"})
    late_baseline = create_baseline(client, seed_basics["project_id"], name="Later")

    early_comparison = client.get(
        f"/api/v1/baselines/{early_baseline['id']}/comparison"
    ).json()
    early_item = next(
        i for i in early_comparison["items"] if i["entity_id"] == activity["id"]
    )
    assert early_item["baseline_end"] == "2026-09-04"  # untouched by the later change

    late_comparison = client.get(
        f"/api/v1/baselines/{late_baseline['id']}/comparison"
    ).json()
    late_item = next(
        i for i in late_comparison["items"] if i["entity_id"] == activity["id"]
    )
    assert late_item["baseline_end"] == "2026-09-14"  # captured the new date


def test_comparison_reflects_drift_after_a_later_change(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics)
    baseline = create_baseline(client, seed_basics["project_id"])

    client.patch(f"/api/v1/activities/{activity['id']}", json={"end_date": "2026-09-11"})

    comparison = client.get(f"/api/v1/baselines/{baseline['id']}/comparison").json()
    item = next(i for i in comparison["items"] if i["entity_id"] == activity["id"])
    assert item["current_end"] == "2026-09-11"
    assert item["delta_end_days"] == 7


def test_comparison_omits_activity_deleted_since_baseline(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics, title="Short-lived task")
    baseline = create_baseline(client, seed_basics["project_id"])
    client.delete(f"/api/v1/activities/{activity['id']}")

    comparison = client.get(f"/api/v1/baselines/{baseline['id']}/comparison").json()
    assert all(i["entity_id"] != activity["id"] for i in comparison["items"])


def test_comparison_includes_milestone_drift(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    milestone = client.post(
        "/api/v1/milestones",
        json={
            "project_id": seed_basics["project_id"],
            "title": "Architecture Freeze",
            "date": "2026-09-18",
            "tag_ids": [],
        },
    ).json()
    baseline = create_baseline(client, seed_basics["project_id"])

    client.patch(f"/api/v1/milestones/{milestone['id']}", json={"date": "2026-09-25"})

    comparison = client.get(f"/api/v1/baselines/{baseline['id']}/comparison").json()
    item = next(
        i
        for i in comparison["items"]
        if i["entity_type"] == "milestone" and i["entity_id"] == milestone["id"]
    )
    assert item["baseline_start"] == "2026-09-18"
    assert item["current_start"] == "2026-09-25"
    assert item["delta_start_days"] == 7


def test_comparison_sorted_by_largest_drift_first(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    small_drift = make_activity(client, seed_basics, title="Small drift")
    big_drift = make_activity(client, seed_basics, title="Big drift")
    baseline = create_baseline(client, seed_basics["project_id"])

    client.patch(f"/api/v1/activities/{small_drift['id']}", json={"end_date": "2026-09-05"})
    client.patch(f"/api/v1/activities/{big_drift['id']}", json={"end_date": "2026-10-04"})

    comparison = client.get(f"/api/v1/baselines/{baseline['id']}/comparison").json()
    titles_in_order = [i["label"] for i in comparison["items"]]
    assert titles_in_order.index("Big drift") < titles_in_order.index("Small drift")


def test_list_baselines_ordered_newest_first(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    create_baseline(client, seed_basics["project_id"], name="First")
    create_baseline(client, seed_basics["project_id"], name="Second")

    baselines = client.get(
        "/api/v1/baselines", params={"project_id": seed_basics["project_id"]}
    ).json()
    assert [b["name"] for b in baselines] == ["Second", "First"]


def test_comparison_unknown_baseline_404(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.get("/api/v1/baselines/9999/comparison")
    assert response.status_code == 404
