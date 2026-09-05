from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.import_export import ImportApplyResponse, ImportPreviewResponse
from app.services import import_activities as import_service

router = APIRouter(prefix="/import", tags=["import"])

TEMPLATE_CSV = (
    ",".join(import_service.EXPECTED_COLUMNS)
    + "\n"
    + "Example task,Short description,2026-09-01,2026-09-15,not_started,normal,0,"
    "Electrical,Jane Doe,\"Jane Doe, John Smith\",\"Design, PCB\"\n"
)


@router.get("/activities/template")
def download_activity_import_template(
    current_user: User = Depends(get_current_user),
) -> Response:
    return Response(
        content=TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_import_template.csv"},
    )


@router.post("/activities/preview", response_model=ImportPreviewResponse)
async def preview_activity_import(
    project_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportPreviewResponse:
    content = await file.read()
    return import_service.preview_import(db, project_id, file.filename or "", content, current_user)


@router.post("/activities/apply", response_model=ImportApplyResponse)
async def apply_activity_import(
    project_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportApplyResponse:
    content = await file.read()
    return import_service.apply_import(db, project_id, file.filename or "", content, current_user)
