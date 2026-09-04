from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_projects_empty(client: TestClient) -> None:
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert response.json() == []
