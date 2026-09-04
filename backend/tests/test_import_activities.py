import io

from fastapi.testclient import TestClient

HEADER = "title,description,start_date,end_date,status,priority,progress_percent,owner_team,owner_user,contributors,tags"


def _csv(*rows: str) -> bytes:
    return (HEADER + "\n" + "\n".join(rows)).encode("utf-8")


def _preview(client: TestClient, project_id: int, content: bytes, filename: str = "import.csv"):
    return client.post(
        "/api/v1/import/activities/preview",
        params={"project_id": project_id},
        files={"file": (filename, content, "text/csv")},
    )


def _apply(client: TestClient, project_id: int, content: bytes, filename: str = "import.csv"):
    return client.post(
        "/api/v1/import/activities/apply",
        params={"project_id": project_id},
        files={"file": (filename, content, "text/csv")},
    )


def test_preview_reports_valid_row_with_no_errors(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    content = _csv("Task A,,2026-09-01,2026-09-10,,,,,,,")
    response = _preview(client, seed_basics["project_id"], content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid_count"] == 1
    assert body["error_count"] == 0
    assert body["rows"][0]["errors"] == []


def test_preview_resolves_team_user_and_tag_by_name(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    content = _csv(
        "Task A,,2026-09-01,2026-09-10,in_progress,high,50,Mechanical,Alice,Bob,Testing"
    )
    response = _preview(client, seed_basics["project_id"], content)
    body = response.json()
    assert body["valid_count"] == 1
    assert body["rows"][0]["errors"] == []


def test_preview_flags_missing_required_fields(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    content = _csv(",Missing everything else,,,,,,,,,")
    response = _preview(client, seed_basics["project_id"], content)
    body = response.json()
    assert body["error_count"] == 1
    errors = body["rows"][0]["errors"]
    assert any("title" in e for e in errors)
    assert any("start_date" in e for e in errors)
    assert any("end_date" in e for e in errors)


def test_preview_flags_end_before_start(client: TestClient, seed_basics: dict[str, int]) -> None:
    content = _csv("Task A,,2026-09-10,2026-09-01,,,,,,,")
    response = _preview(client, seed_basics["project_id"], content)
    errors = response.json()["rows"][0]["errors"]
    assert any("end_date must not be before start_date" in e for e in errors)


def test_preview_flags_unknown_team_user_and_tag(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    content = _csv(
        "Task A,,2026-09-01,2026-09-10,,,,Nonexistent Team,Nobody,Nobody,Nonexistent Tag"
    )
    response = _preview(client, seed_basics["project_id"], content)
    errors = response.json()["rows"][0]["errors"]
    assert any("unknown owner_team" in e for e in errors)
    assert any("unknown owner_user" in e for e in errors)
    assert any("unknown contributor" in e for e in errors)
    assert any("unknown tag" in e for e in errors)


def test_preview_flags_invalid_status_and_priority(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    content = _csv("Task A,,2026-09-01,2026-09-10,bogus,extreme,,,,,")
    response = _preview(client, seed_basics["project_id"], content)
    errors = response.json()["rows"][0]["errors"]
    assert any("invalid status" in e for e in errors)
    assert any("invalid priority" in e for e in errors)


def test_preview_does_not_write_anything(client: TestClient, seed_basics: dict[str, int]) -> None:
    content = _csv("Task A,,2026-09-01,2026-09-10,,,,,,,")
    _preview(client, seed_basics["project_id"], content)
    listing = client.get(
        "/api/v1/activities", params={"project_id": seed_basics["project_id"]}
    ).json()
    assert listing == []


def test_apply_creates_only_valid_rows(client: TestClient, seed_basics: dict[str, int]) -> None:
    content = _csv(
        "Task A,,2026-09-01,2026-09-10,,,,,,,",
        ",Missing dates,,,,,,,,,",  # non-blank line, missing required fields -> invalid
    )
    response = _apply(client, seed_basics["project_id"], content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created_count"] == 1
    assert body["skipped_count"] == 1

    listing = client.get(
        "/api/v1/activities", params={"project_id": seed_basics["project_id"]}
    ).json()
    assert len(listing) == 1
    assert listing[0]["title"] == "Task A"


def test_apply_links_resolved_team_user_contributor_and_tag(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    content = _csv(
        "Task A,,2026-09-01,2026-09-10,,,,Mechanical,Alice,Bob,Testing"
    )
    response = _apply(client, seed_basics["project_id"], content)
    activity_id = response.json()["rows"][0]["activity_id"]
    activity = client.get(f"/api/v1/activities/{activity_id}").json()
    assert activity["owner_team"]["name"] == "Mechanical"
    assert activity["owner_user"]["name"] == "Alice"
    assert [c["name"] for c in activity["contributors"]] == ["Bob"]
    assert [t["name"] for t in activity["tags"]] == ["Testing"]


def test_apply_reparses_rather_than_trusting_client_state(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    # A row that would be invalid is still rejected by /apply even though
    # nothing prevents a client from calling it without ever previewing.
    content = _csv("Task A,,2026-09-10,2026-09-01,,,,,,,")
    response = _apply(client, seed_basics["project_id"], content)
    body = response.json()
    assert body["created_count"] == 0
    assert body["skipped_count"] == 1


def test_import_rejects_unsupported_file_type(
    client: TestClient, seed_basics: dict[str, int]
) -> None:
    response = _preview(
        client, seed_basics["project_id"], b"not a csv", filename="import.txt"
    )
    assert response.status_code == 422


def test_import_xlsx_file(client: TestClient, seed_basics: dict[str, int]) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(HEADER.split(","))
    ws.append(["Task A", "", "2026-09-01", "2026-09-10", "", "", "", "", "", "", ""])
    buffer = io.BytesIO()
    wb.save(buffer)

    response = client.post(
        "/api/v1/import/activities/preview",
        params={"project_id": seed_basics["project_id"]},
        files={
            "file": (
                "import.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid_count"] == 1
    assert body["rows"][0]["title"] == "Task A"


def test_download_template_returns_csv_with_expected_headers(client: TestClient) -> None:
    response = client.get("/api/v1/import/activities/template")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    first_line = response.text.splitlines()[0]
    assert first_line == HEADER
