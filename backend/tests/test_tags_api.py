from fastapi.testclient import TestClient


def test_create_update_delete_tag(client: TestClient, seed_basics: dict[str, int]) -> None:
    create = client.post(
        "/api/v1/tags",
        json={"project_id": seed_basics["project_id"], "name": "Sponsor", "color": "#ff9900"},
    )
    assert create.status_code == 201, create.text
    tag = create.json()
    assert tag["name"] == "Sponsor"

    update = client.patch(f"/api/v1/tags/{tag['id']}", json={"name": "Sponsors"})
    assert update.status_code == 200, update.text
    assert update.json()["name"] == "Sponsors"

    delete = client.delete(f"/api/v1/tags/{tag['id']}")
    assert delete.status_code == 204

    listing = client.get(
        "/api/v1/tags", params={"project_id": seed_basics["project_id"]}
    ).json()
    assert all(t["id"] != tag["id"] for t in listing)


def test_deleted_tag_omitted_from_list_but_others_remain(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    listing_before = client.get(
        "/api/v1/tags", params={"project_id": seed_basics["project_id"]}
    ).json()
    assert any(t["id"] == seed_basics["tag_id"] for t in listing_before)


def test_non_admin_cannot_manage_tags(client: TestClient, seed_basics: dict[str, int]) -> None:
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login", json={"email": "bob@example.org", "password": "seed-user-password-123"}
    )
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf", "")

    response = client.post(
        "/api/v1/tags",
        json={"project_id": seed_basics["project_id"], "name": "Sneaky"},
    )
    assert response.status_code == 403
