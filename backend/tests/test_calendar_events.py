from fastapi.testclient import TestClient


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
        "/api/v1/calendar-events", params={"event_type": "social"}
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
        params={"date_from": "2026-09-07T00:00:00", "date_to": "2026-09-13T23:59:59"},
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
