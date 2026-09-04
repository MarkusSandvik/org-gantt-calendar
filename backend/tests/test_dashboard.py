import datetime as dt

from fastapi.testclient import TestClient

TODAY = dt.date.today()
MONDAY = TODAY - dt.timedelta(days=TODAY.weekday())
SUNDAY = MONDAY + dt.timedelta(days=6)


def make_activity(client: TestClient, seed_basics: dict[str, int], **overrides) -> dict:
    payload = {
        "project_id": seed_basics["project_id"],
        "title": "Some activity",
        "start_date": str(MONDAY),
        "end_date": str(SUNDAY),
        "status": "in_progress",
        "contributor_user_ids": [],
        "tag_ids": [],
    }
    payload.update(overrides)
    return client.post("/api/v1/activities", json=payload).json()


def get_summary(client: TestClient, project_id: int) -> dict:
    response = client.get("/api/v1/dashboard/summary", params={"project_id": project_id})
    assert response.status_code == 200, response.text
    return response.json()


def test_week_counts_reflect_current_data(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    make_activity(client, seed_basics, title="In progress thing", status="in_progress")
    make_activity(client, seed_basics, title="Delayed thing", status="delayed")
    make_activity(client, seed_basics, title="Blocked thing", status="blocked")

    summary = get_summary(client, seed_basics["project_id"])
    assert summary["week_counts"]["active_tasks"] == 1
    assert summary["week_counts"]["delayed"] == 1
    assert summary["week_counts"]["blocked"] == 1
    assert summary["iso_year"], summary["iso_week"]
    assert summary["week_start"] == str(MONDAY)
    assert summary["week_end"] == str(SUNDAY)


def test_week_counts_are_zero_when_nothing_matches(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    summary = get_summary(client, seed_basics["project_id"])
    assert summary["week_counts"] == {
        "active_tasks": 0,
        "milestones_this_week": 0,
        "delayed": 0,
        "blocked": 0,
        "social_activities": 0,
        "meetings": 0,
        "upcoming_deadlines": 0,
    }
    # Zero categories are still returned by the API — the frontend decides
    # what to hide, per the master spec's "don't show meaningless zeros" rule.
    assert summary["upcoming_milestones"] == []
    assert summary["attention_required"] == []


def test_upcoming_milestones_excludes_completed_and_missed(
    client: TestClient, db_session, seed_basics: dict[str, int]
) -> None:
    from app.models.milestone import Milestone

    db_session.add_all(
        [
            Milestone(
                project_id=seed_basics["project_id"],
                title="Still coming",
                date=TODAY + dt.timedelta(days=10),
                status="on_track",
            ),
            Milestone(
                project_id=seed_basics["project_id"],
                title="Already done",
                date=TODAY + dt.timedelta(days=5),
                status="completed",
            ),
            Milestone(
                project_id=seed_basics["project_id"],
                title="Missed it",
                date=TODAY + dt.timedelta(days=2),
                status="missed",
            ),
            Milestone(
                project_id=seed_basics["project_id"],
                title="In the past",
                date=TODAY - dt.timedelta(days=2),
                status="on_track",
            ),
        ]
    )
    db_session.commit()

    summary = get_summary(client, seed_basics["project_id"])
    titles = [m["title"] for m in summary["upcoming_milestones"]]
    assert titles == ["Still coming"]


def test_attention_required_delayed_day_count(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    make_activity(
        client,
        seed_basics,
        title="Overdue thing",
        status="delayed",
        start_date=str(TODAY - dt.timedelta(days=20)),
        end_date=str(TODAY - dt.timedelta(days=6)),
    )

    summary = get_summary(client, seed_basics["project_id"])
    item = next(i for i in summary["attention_required"] if i["title"] == "Overdue thing")
    assert item["detail"] == "6 days delayed"


def test_attention_required_blocked_names_incomplete_predecessor(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    predecessor = make_activity(
        client, seed_basics, title="PCB delivery", status="in_progress"
    )
    blocked = make_activity(client, seed_basics, title="CAN Integration", status="blocked")
    client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": predecessor["id"],
            "successor_type": "activity",
            "successor_id": blocked["id"],
        },
    )

    summary = get_summary(client, seed_basics["project_id"])
    item = next(i for i in summary["attention_required"] if i["title"] == "CAN Integration")
    assert item["detail"] == "Blocked by PCB delivery"


def test_attention_required_blocked_falls_back_without_dependency(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    make_activity(client, seed_basics, title="Mystery block", status="blocked")

    summary = get_summary(client, seed_basics["project_id"])
    item = next(i for i in summary["attention_required"] if i["title"] == "Mystery block")
    assert item["detail"] == "Blocked"
