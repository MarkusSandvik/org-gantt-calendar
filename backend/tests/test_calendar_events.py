from fastapi.testclient import TestClient

from tests.conftest import SEED_USER_PASSWORD


def make_payload(seed_basics: dict[str, int], **overrides) -> dict:
    payload = {
        "project_id": seed_basics["project_id"],
        "title": "Embedded weekly meeting",
        "description": None,
        "event_type": "meeting",
        "start_datetime": "2026-09-07T16:00:00",
        "end_datetime": "2026-09-07T17:00:00",
        "all_day": False,
        "location": None,
        "team_id": seed_basics["team_id"],
        "owner_user_id": None,
        "related_activity_id": None,
    }
    payload.update(overrides)
    return payload


def test_create_calendar_event(client: TestClient, seed_basics: dict[str, int]) -> None:
    response = client.post("/api/v1/calendar-events", json=make_payload(seed_basics))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Embedded weekly meeting"
    assert body["team"]["id"] == seed_basics["team_id"]
    assert body["event_type"] == "meeting"


def test_create_calendar_event_rejects_end_before_start(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics,
            start_datetime="2026-09-07T17:00:00",
            end_datetime="2026-09-07T16:00:00",
        ),
    )
    assert response.status_code == 422


def test_create_all_teams_calendar_event(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, team_id=None, all_teams=True),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["all_teams"] is True
    assert body["team"] is None


def test_create_calendar_event_rejects_all_teams_with_team(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, team_id=seed_basics["team_id"], all_teams=True),
    )
    assert response.status_code == 422


def test_non_admin_cannot_create_all_teams_calendar_event(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login", json={"email": "bob@example.org", "password": SEED_USER_PASSWORD}
    )
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf", "")

    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, team_id=None, all_teams=True),
    )
    assert response.status_code == 403


def test_create_calendar_event_rejects_unknown_team(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events", json=make_payload(seed_basics, team_id=9999)
    )
    assert response.status_code == 404


def test_list_calendar_events_filter_by_event_type(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, title="Board meeting", event_type="meeting"),
    )
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, title="Team dinner", event_type="social"),
    )

    result = client.get(
        "/api/v1/calendar-events",
        params={"project_id": seed_basics["project_id"], "event_type": "social"},
    ).json()
    assert len(result) == 1
    assert result[0]["title"] == "Team dinner"


def test_list_calendar_events_date_range_overlap(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    # Default fixture event: Mon 7 Sep 16:00-17:00.
    client.post("/api/v1/calendar-events", json=make_payload(seed_basics))
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics,
            title="Next week thing",
            start_datetime="2026-09-14T16:00:00",
            end_datetime="2026-09-14T17:00:00",
        ),
    )

    in_week = client.get(
        "/api/v1/calendar-events",
        params={
            "project_id": seed_basics["project_id"],
            "date_from": "2026-09-07T00:00:00",
            "date_to": "2026-09-13T23:59:59",
        },
    ).json()
    assert len(in_week) == 1
    assert in_week[0]["title"] == "Embedded weekly meeting"


def test_update_calendar_event_partial(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    created = client.post(
        "/api/v1/calendar-events", json=make_payload(seed_basics)
    ).json()

    response = client.patch(
        f"/api/v1/calendar-events/{created['id']}", json={"location": "Room 204"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "Room 204"
    assert body["title"] == "Embedded weekly meeting"  # untouched


def test_delete_calendar_event(client: TestClient, seed_basics: dict[str, int]) -> None:
    created = client.post(
        "/api/v1/calendar-events", json=make_payload(seed_basics)
    ).json()

    response = client.delete(f"/api/v1/calendar-events/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/calendar-events/{created['id']}").status_code == 404


def test_list_calendar_events_filter_by_owner_user(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, title="Alice's event", owner_user_id=seed_basics["user_id"]),
    )
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics, title="Bob's event", owner_user_id=seed_basics["other_user_id"]
        ),
    )

    mine = client.get(
        "/api/v1/calendar-events",
        params={"project_id": seed_basics["project_id"], "owner_user_id": seed_basics["user_id"]},
    ).json()
    assert [e["title"] for e in mine] == ["Alice's event"]


def test_create_calendar_event_with_tags(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, tag_ids=[seed_basics["tag_id"]]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert [t["id"] for t in body["tags"]] == [seed_basics["tag_id"]]


def test_create_calendar_event_rejects_unknown_tag(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events", json=make_payload(seed_basics, tag_ids=[9999])
    )
    assert response.status_code == 404


def test_update_calendar_event_tags(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    created = client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, tag_ids=[seed_basics["tag_id"]]),
    ).json()

    response = client.patch(
        f"/api/v1/calendar-events/{created['id']}", json={"tag_ids": []}
    )
    assert response.status_code == 200
    assert response.json()["tags"] == []


def test_list_calendar_events_filter_by_tag(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, title="Tagged", tag_ids=[seed_basics["tag_id"]]),
    )
    client.post(
        "/api/v1/calendar-events", json=make_payload(seed_basics, title="Untagged")
    )

    result = client.get(
        "/api/v1/calendar-events",
        params={"project_id": seed_basics["project_id"], "tag_id": seed_basics["tag_id"]},
    ).json()
    assert [e["title"] for e in result] == ["Tagged"]


def test_list_calendar_events_all_teams_only(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, title="Org-wide", team_id=None, all_teams=True),
    )
    client.post(
        "/api/v1/calendar-events", json=make_payload(seed_basics, title="Team-only")
    )

    result = client.get(
        "/api/v1/calendar-events",
        params={"project_id": seed_basics["project_id"], "all_teams_only": True},
    ).json()
    assert [e["title"] for e in result] == ["Org-wide"]


def _list_titled(client: TestClient, project_id: int, title: str) -> list[dict]:
    result = client.get("/api/v1/calendar-events", params={"project_id": project_id, "q": title}).json()
    return sorted(result, key=lambda e: e["start_datetime"])


def test_create_weekly_recurring_event_generates_occurrences(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics,
            title="Weekly Standup",
            recurrence_frequency="weekly",
            recurrence_end_date="2026-09-28",
        ),
    )
    assert response.status_code == 201, response.text
    leader = response.json()
    assert leader["recurrence_frequency"] == "weekly"
    assert leader["recurrence_end_date"] == "2026-09-28"
    assert leader["recurrence_group_id"] == leader["id"]

    occurrences = _list_titled(client, seed_basics["project_id"], "Weekly Standup")
    assert [o["start_datetime"][:10] for o in occurrences] == [
        "2026-09-07",
        "2026-09-14",
        "2026-09-21",
        "2026-09-28",
    ]
    assert all(o["recurrence_group_id"] == leader["id"] for o in occurrences)
    # Duration (1 hour, per make_payload) is preserved on every occurrence.
    for o in occurrences:
        assert o["start_datetime"][11:] == "16:00:00"
        assert o["end_datetime"][11:] == "17:00:00"


def test_recurrence_requires_frequency_and_end_date_together(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    only_frequency = client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, recurrence_frequency="weekly"),
    )
    assert only_frequency.status_code == 422

    only_end_date = client.post(
        "/api/v1/calendar-events",
        json=make_payload(seed_basics, recurrence_end_date="2026-09-28"),
    )
    assert only_end_date.status_code == 422


def test_recurrence_end_date_before_start_rejected(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics, recurrence_frequency="weekly", recurrence_end_date="2026-09-01"
        ),
    )
    assert response.status_code == 422


def test_monthly_recurrence_handles_month_end_overflow(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics,
            title="Month End Sync",
            start_datetime="2026-01-31T16:00:00",
            end_datetime="2026-01-31T17:00:00",
            recurrence_frequency="monthly",
            recurrence_end_date="2026-04-30",
        ),
    )
    assert response.status_code == 201, response.text
    occurrences = _list_titled(client, seed_basics["project_id"], "Month End Sync")
    # Feb has no 31st, so it falls back to the last day of that month; Mar
    # and Apr both have 31/30 days respectively.
    assert [o["start_datetime"][:10] for o in occurrences] == [
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
        "2026-04-30",
    ]


def test_recurrence_rejects_excessive_occurrence_count(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics, recurrence_frequency="daily", recurrence_end_date="2027-12-31"
        ),
    )
    assert response.status_code == 422


def test_delete_single_occurrence_keeps_the_rest_of_the_series(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics,
            title="Delete Single Series",
            recurrence_frequency="weekly",
            recurrence_end_date="2026-09-28",
        ),
    )
    occurrences = _list_titled(client, seed_basics["project_id"], "Delete Single Series")
    assert len(occurrences) == 4

    second = occurrences[1]
    response = client.delete(f"/api/v1/calendar-events/{second['id']}")
    assert response.status_code == 204

    remaining = _list_titled(client, seed_basics["project_id"], "Delete Single Series")
    assert [o["start_datetime"][:10] for o in remaining] == [
        "2026-09-07",
        "2026-09-21",
        "2026-09-28",
    ]


def test_delete_future_removes_this_and_later_occurrences_only(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/calendar-events",
        json=make_payload(
            seed_basics,
            title="Delete Future Series",
            recurrence_frequency="weekly",
            recurrence_end_date="2026-09-28",
        ),
    )
    occurrences = _list_titled(client, seed_basics["project_id"], "Delete Future Series")
    assert len(occurrences) == 4

    second = occurrences[1]
    response = client.delete(
        f"/api/v1/calendar-events/{second['id']}", params={"delete_future": True}
    )
    assert response.status_code == 204

    remaining = _list_titled(client, seed_basics["project_id"], "Delete Future Series")
    assert [o["start_datetime"][:10] for o in remaining] == ["2026-09-07"]
