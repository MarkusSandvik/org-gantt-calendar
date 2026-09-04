from pydantic import BaseModel


class ImportRowResult(BaseModel):
    row_number: int
    title: str
    start_date: str
    end_date: str
    status: str
    priority: str
    progress_percent: str
    owner_team: str
    owner_user: str
    contributors: str
    tags: str
    errors: list[str]
    activity_id: int | None = None


class ImportPreviewResponse(BaseModel):
    rows: list[ImportRowResult]
    valid_count: int
    error_count: int


class ImportApplyResponse(BaseModel):
    created_count: int
    skipped_count: int
    rows: list[ImportRowResult]
