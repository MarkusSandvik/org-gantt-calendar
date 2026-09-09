from fastapi.testclient import TestClient

from tests.conftest import SEED_USER_PASSWORD


def make_activity(client: TestClient, project_id: int, title: str, **overrides) -> dict:
    payload = {
        "project_id": project_id,
        "title": title,
        "start_date": "2026-08-01",
        "end_date": "2026-08-10",
        "contributor_user_ids": [],
        "tag_ids": [],
    }
    payload.update(overrides)
    return client.post("/api/v1/activities", json=payload).json()


def make_second_project(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": "Team 28", "slug": "team-28", "season_label": "2027/28"},
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Project CRUD / status transitions
# ---------------------------------------------------------------------------


def test_admin_can_create_project(client: TestClient, seed_basics: dict[str, int]) -> None:
    project = make_second_project(client)
    assert project["status"] == "draft"
    assert project["is_default"] is False
    assert project["slug"] == "team-28"


def test_project_slug_auto_derived_and_unique(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    first = client.post("/api/v1/projects", json={"name": "Team 29"}).json()
    second = client.post("/api/v1/projects", json={"name": "Team 29"}).json()
    assert first["slug"] == "team-29"
    assert second["slug"] != first["slug"]


def test_project_slug_avoids_reserved_route_words(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    """A project literally named "Gantt" or "Admin" must not get that exact
    slug — the frontend router treats a first URL segment matching one of
    those as the old flat route, not a project, so the project would be
    permanently unreachable."""
    project = client.post("/api/v1/projects", json={"name": "Gantt"}).json()
    assert project["slug"] != "gantt"


def test_non_admin_cannot_create_project(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login", json={"email": "bob@example.org", "password": SEED_USER_PASSWORD}
    )
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf", "")

    response = client.post("/api/v1/projects", json={"name": "Sneaky Project"})
    assert response.status_code == 403


def test_copy_structure_duplicates_teams_and_tags_only(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.post(
        "/api/v1/tags", json={"project_id": seed_basics["project_id"], "name": "Sponsor"}
    )
    make_activity(client, seed_basics["project_id"], "Old season task")

    response = client.post(
        "/api/v1/projects",
        json={
            "name": "Team 28",
            "slug": "team-28",
            "copy_structure_from_project_id": seed_basics["project_id"],
        },
    )
    assert response.status_code == 201, response.text
    new_project = response.json()

    new_teams = client.get(
        "/api/v1/teams", params={"project_id": new_project["id"]}
    ).json()
    assert len(new_teams) == 1
    assert new_teams[0]["name"] == "Mechanical"
    assert new_teams[0]["members"] == []  # structure only — no memberships copied

    new_tags = client.get("/api/v1/tags", params={"project_id": new_project["id"]}).json()
    assert "Sponsor" in {t["name"] for t in new_tags}

    new_activities = client.get(
        "/api/v1/activities", params={"project_id": new_project["id"]}
    ).json()
    assert new_activities == []  # no schedule data copied


def test_copy_structure_from_missing_project_404s(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = client.post(
        "/api/v1/projects",
        json={"name": "Team 29", "copy_structure_from_project_id": 9999},
    )
    assert response.status_code == 404


def test_activating_project_completes_previous_default(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    project = make_second_project(client)

    response = client.patch(
        f"/api/v1/projects/{project['id']}/status", json={"status": "active"}
    )
    assert response.status_code == 200, response.text
    activated = response.json()
    assert activated["status"] == "active"
    assert activated["is_default"] is True

    original = client.get(f"/api/v1/projects/{seed_basics['project_id']}").json()
    assert original["status"] == "completed"
    assert original["is_default"] is False


def test_invalid_status_transition_rejected(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    project = make_second_project(client)
    response = client.patch(
        f"/api/v1/projects/{project['id']}/status", json={"status": "archived"}
    )
    assert response.status_code == 200, response.text  # DRAFT -> ARCHIVED is allowed

    # ARCHIVED is a dead end: nothing can move it anywhere else.
    response = client.patch(
        f"/api/v1/projects/{project['id']}/status", json={"status": "active"}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Cross-project isolation
# ---------------------------------------------------------------------------


def test_activity_list_does_not_leak_across_projects(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    other = make_second_project(client)
    make_activity(client, seed_basics["project_id"], "Project A task")
    make_activity(client, other["id"], "Project B task")

    titles_a = {
        a["title"]
        for a in client.get(
            "/api/v1/activities", params={"project_id": seed_basics["project_id"]}
        ).json()
    }
    titles_b = {
        a["title"]
        for a in client.get("/api/v1/activities", params={"project_id": other["id"]}).json()
    }
    assert "Project A task" in titles_a and "Project B task" not in titles_a
    assert "Project B task" in titles_b and "Project A task" not in titles_b


def test_dependency_rejected_across_projects(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    other = make_second_project(client)
    a = make_activity(client, seed_basics["project_id"], "A in project 1")
    b = make_activity(client, other["id"], "B in project 2")

    response = client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a["id"],
            "successor_type": "activity",
            "successor_id": b["id"],
        },
    )
    assert response.status_code == 422


def test_dependency_list_is_project_scoped(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    other = make_second_project(client)
    a1 = make_activity(client, seed_basics["project_id"], "A1")
    a2 = make_activity(client, seed_basics["project_id"], "A2")
    b1 = make_activity(client, other["id"], "B1")
    b2 = make_activity(client, other["id"], "B2")

    client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a1["id"],
            "successor_type": "activity",
            "successor_id": a2["id"],
        },
    )
    client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": b1["id"],
            "successor_type": "activity",
            "successor_id": b2["id"],
        },
    )

    deps_a = client.get(
        "/api/v1/dependencies", params={"project_id": seed_basics["project_id"]}
    ).json()
    deps_b = client.get("/api/v1/dependencies", params={"project_id": other["id"]}).json()
    assert len(deps_a) == 1 and deps_a[0]["predecessor_label"] == "A1"
    assert len(deps_b) == 1 and deps_b[0]["predecessor_label"] == "B1"


def test_search_scoped_to_project_id_does_not_leak_across_projects(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    other = make_second_project(client)
    make_activity(client, seed_basics["project_id"], "Uniquename Alpha")
    make_activity(client, other["id"], "Uniquename Beta")

    results_a = client.get(
        "/api/v1/search", params={"q": "Uniquename", "project_id": seed_basics["project_id"]}
    ).json()
    labels_a = {r["label"] for r in results_a}
    assert labels_a == {"Uniquename Alpha"}

    results_b = client.get(
        "/api/v1/search", params={"q": "Uniquename", "project_id": other["id"]}
    ).json()
    labels_b = {r["label"] for r in results_b}
    assert labels_b == {"Uniquename Beta"}

    # Without a project_id, search is intentionally unscoped (used only by
    # callers that haven't resolved a project yet) and sees both.
    results_unscoped = client.get("/api/v1/search", params={"q": "Uniquename"}).json()
    assert {r["label"] for r in results_unscoped} == {"Uniquename Alpha", "Uniquename Beta"}


def test_rescheduling_never_propagates_across_projects(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    """A same-named/same-dated activity in another project must never be
    touched by a reschedule in this one — the scheduling graph is loaded
    per-project specifically to guarantee this."""
    other = make_second_project(client)
    a1 = make_activity(client, seed_basics["project_id"], "A1", end_date="2026-08-10")
    a2 = make_activity(
        client, seed_basics["project_id"], "A2", start_date="2026-08-11", end_date="2026-08-15"
    )
    client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a1["id"],
            "successor_type": "activity",
            "successor_id": a2["id"],
        },
    )
    # Same id-shape coincidence risk: an unrelated activity in the other
    # project with an overlapping date range.
    b1 = make_activity(client, other["id"], "B1", end_date="2026-08-10")

    response = client.post(
        "/api/v1/scheduling/apply",
        json={
            "entity_type": "activity",
            "entity_id": a1["id"],
            "new_start_date": "2026-08-05",
            "new_end_date": "2026-08-20",
            "reason": "test reason",
        },
    )
    assert response.status_code == 200, response.text

    b1_after = client.get(f"/api/v1/activities/{b1['id']}").json()
    assert b1_after["end_date"] == "2026-08-10"  # untouched


# ---------------------------------------------------------------------------
# Lead-uniqueness must not rewrite history on a completed/archived project
# ---------------------------------------------------------------------------


def test_completed_project_rejects_new_activity(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    client.patch(
        f"/api/v1/projects/{seed_basics['project_id']}/status", json={"status": "completed"}
    )
    response = client.post(
        "/api/v1/activities",
        json={
            "project_id": seed_basics["project_id"],
            "title": "Too late",
            "start_date": "2026-08-01",
            "end_date": "2026-08-10",
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    )
    assert response.status_code == 422
    assert "read-only" in response.json()["detail"]


def test_archived_project_rejects_activity_update_and_delete(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    activity = make_activity(client, seed_basics["project_id"], "Will be locked")
    client.patch(
        f"/api/v1/projects/{seed_basics['project_id']}/status", json={"status": "completed"}
    )
    client.patch(
        f"/api/v1/projects/{seed_basics['project_id']}/status", json={"status": "archived"}
    )

    update_response = client.patch(
        f"/api/v1/activities/{activity['id']}",
        json={"title": "Edited after archive", "reason": "trying anyway"},
    )
    assert update_response.status_code == 422

    delete_response = client.delete(f"/api/v1/activities/{activity['id']}")
    assert delete_response.status_code == 422


def test_completed_project_rejects_new_team_and_dependency(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    a1 = make_activity(client, seed_basics["project_id"], "A1", end_date="2026-08-10")
    a2 = make_activity(
        client, seed_basics["project_id"], "A2", start_date="2026-08-11", end_date="2026-08-15"
    )
    client.patch(
        f"/api/v1/projects/{seed_basics['project_id']}/status", json={"status": "completed"}
    )

    team_response = client.post(
        "/api/v1/teams",
        json={"project_id": seed_basics["project_id"], "name": "Late Team", "category": "hardware"},
    )
    assert team_response.status_code == 422

    dep_response = client.post(
        "/api/v1/dependencies",
        json={
            "predecessor_type": "activity",
            "predecessor_id": a1["id"],
            "successor_type": "activity",
            "successor_id": a2["id"],
        },
    )
    assert dep_response.status_code == 422


def test_active_project_still_allows_writes(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    """Sanity check: the read-only gate must not accidentally lock down a
    normal DRAFT/ACTIVE project."""
    response = client.post(
        "/api/v1/activities",
        json={
            "project_id": seed_basics["project_id"],
            "title": "Still allowed",
            "start_date": "2026-08-01",
            "end_date": "2026-08-10",
            "contributor_user_ids": [],
            "tag_ids": [],
        },
    )
    assert response.status_code == 201, response.text


def test_promoting_lead_in_new_project_does_not_demote_archived_project_lead(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    # Alice leads the (still-active) seed project's team.
    client.put(
        f"/api/v1/users/{seed_basics['user_id']}/team-memberships",
        json={"team_id": seed_basics["team_id"], "team_role": "lead"},
    )

    # Archive that project — its Lead record is now history.
    client.patch(
        f"/api/v1/projects/{seed_basics['project_id']}/status", json={"status": "archived"}
    )

    # Create a new project/team and make Alice Lead there too.
    new_project = make_second_project(client)
    new_team = client.post(
        "/api/v1/teams",
        json={"project_id": new_project["id"], "name": "Embedded", "category": "hardware"},
    ).json()
    client.put(
        f"/api/v1/users/{seed_basics['user_id']}/team-memberships",
        json={"team_id": new_team["id"], "team_role": "lead"},
    )

    user = client.get("/api/v1/users/admin").json()
    alice = next(u for u in user if u["id"] == seed_basics["user_id"])
    roles = {m["team_id"]: m["team_role"] for m in alice["team_memberships"]}
    assert roles[seed_basics["team_id"]] == "lead"  # untouched, still historical Lead
    assert roles[new_team["id"]] == "lead"
