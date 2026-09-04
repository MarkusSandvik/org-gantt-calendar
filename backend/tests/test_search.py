from fastapi.testclient import TestClient


def test_search_returns_matches_across_types(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/activities",
        json={
            "project_id": seed_basics["project_id"],
            "title": "Pool Testing Rig",
            "start_date": "2026-08-05",
            "end_date": "2026-09-20",
            "owner_team_id": seed_basics["team_id"],
            "contributor_user_ids": [],
            "tag_ids": [seed_basics["tag_id"]],
        },
    )

    result = client.get("/api/v1/search", params={"q": "Test"}).json()
    types = {r["type"] for r in result}
    labels = {r["label"] for r in result}
    assert "activity" in types
    assert "tag" in types  # seed_basics tag is named "Testing"
    assert "Pool Testing Rig" in labels
    assert "Testing" in labels


def test_search_requires_minimum_length(client: TestClient, seed_basics: dict[str, int]) -> None:
    assert client.get("/api/v1/search", params={"q": "a"}).json() == []
    assert client.get("/api/v1/search", params={"q": ""}).json() == []


def test_search_no_matches(client: TestClient, seed_basics: dict[str, int]) -> None:
    result = client.get("/api/v1/search", params={"q": "zzz_no_match_zzz"}).json()
    assert result == []
