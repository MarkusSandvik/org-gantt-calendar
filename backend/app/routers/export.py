from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import export_data as export_service

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/activities.csv")
def export_activities_csv(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    content = export_service.export_activities_csv(db, project_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activities_export.csv"},
    )


@router.get("/plan.xlsx")
def export_plan_xlsx(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    content = export_service.export_plan_xlsx(db, project_id)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plan_export.xlsx"},
    )
