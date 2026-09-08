from fastapi.testclient import TestClient


def test_list_teams_includes_members_and_leads(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.put(
        f"/api/v1/users/{seed_basics['user_id']}/team-memberships",
        json={"team_id": seed_basics["team_id"], "team_role": "lead"},
    )
    client.put(
        f"/api/v1/users/{seed_basics['other_user_id']}/team-memberships",
        json={"team_id": seed_basics["team_id"], "team_role": "member"},
    )

    response = client.get("/api/v1/teams", params={"project_id": seed_basics["project_id"]})
    assert response.status_code == 200, response.text
    team = next(t for t in response.json() if t["id"] == seed_basics["team_id"])
    roles = {m["email"]: m["team_role"] for m in team["members"]}
    assert roles == {"alice@example.org": "lead", "bob@example.org": "member"}


def test_create_update_delete_team(client: TestClient, seed_basics: dict[str, int]) -> None:
    create = client.post(
        "/api/v1/teams",
        json={
            "project_id": seed_basics["project_id"],
            "name": "Software",
            "category": "software",
            "color": "#336699",
        },
    )
    assert create.status_code == 201, create.text
    team = create.json()
    assert team["name"] == "Software"
    assert team["members"] == []

    update = client.patch(f"/api/v1/teams/{team['id']}", json={"name": "Firmware"})
    assert update.status_code == 200, update.text
    assert update.json()["name"] == "Firmware"

    delete = client.delete(f"/api/v1/teams/{team['id']}")
    assert delete.status_code == 204

    listing = client.get(
        "/api/v1/teams", params={"project_id": seed_basics["project_id"]}
    ).json()
    assert all(t["id"] != team["id"] for t in listing)


def test_non_admin_cannot_manage_teams(client: TestClient, seed_basics: dict[str, int]) -> None:
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login", json={"email": "bob@example.org", "password": "seed-user-password-123"}
    )
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf", "")

    response = client.post(
        "/api/v1/teams",
        json={"project_id": seed_basics["project_id"], "name": "Sneaky", "category": "software"},
    )
    assert response.status_code == 403
