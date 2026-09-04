from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.baseline import Baseline, BaselineActivity, BaselineMilestone
from app.models.milestone import Milestone
from app.schemas.baseline import (
    BaselineComparison,
    BaselineCreate,
    BaselineDriftItem,
    BaselineRead,
)


def create_baseline(
    db: Session, project_id: int, payload: BaselineCreate, user_id: int
) -> BaselineRead:
    """Snapshots every activity's and milestone's current planned dates.
    Each call creates a brand new Baseline row — existing baselines are
    never touched, so schedule drift can always be measured against any
    past snapshot, not just the most recent one."""
    baseline = Baseline(
        project_id=project_id, name=payload.name, note=payload.note, created_by_id=user_id
    )
    db.add(baseline)
    db.flush()

    activities = db.scalars(select(Activity).where(Activity.project_id == project_id)).all()
    for activity in activities:
        db.add(
            BaselineActivity(
                baseline_id=baseline.id,
                activity_id=activity.id,
                planned_start_date=activity.start_date,
                planned_end_date=activity.end_date,
            )
        )

    milestones = db.scalars(
        select(Milestone).where(Milestone.project_id == project_id)
    ).all()
    for milestone in milestones:
        db.add(
            BaselineMilestone(
                baseline_id=baseline.id,
                milestone_id=milestone.id,
                planned_date=milestone.date,
            )
        )

    db.commit()
    db.refresh(baseline)
    return BaselineRead.model_validate(baseline)


def list_baselines(db: Session, project_id: int) -> list[BaselineRead]:
    baselines = db.scalars(
        select(Baseline)
        .where(Baseline.project_id == project_id)
        .order_by(Baseline.created_at.desc())
    ).all()
    return [BaselineRead.model_validate(b) for b in baselines]


def get_baseline_comparison(db: Session, baseline_id: int) -> BaselineComparison:
    baseline = db.get(Baseline, baseline_id)
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")

    items: list[BaselineDriftItem] = []

    for snapshot in baseline.activity_snapshots:
        activity = db.get(Activity, snapshot.activity_id)
        if activity is None:
            continue  # deleted since the baseline was taken
        items.append(
            BaselineDriftItem(
                entity_type="activity",
                entity_id=activity.id,
                label=activity.title,
                baseline_start=snapshot.planned_start_date,
                baseline_end=snapshot.planned_end_date,
                current_start=activity.start_date,
                current_end=activity.end_date,
                delta_start_days=(activity.start_date - snapshot.planned_start_date).days,
                delta_end_days=(activity.end_date - snapshot.planned_end_date).days,
            )
        )

    for snapshot in baseline.milestone_snapshots:
        milestone = db.get(Milestone, snapshot.milestone_id)
        if milestone is None:
            continue
        items.append(
            BaselineDriftItem(
                entity_type="milestone",
                entity_id=milestone.id,
                label=milestone.title,
                baseline_start=snapshot.planned_date,
                baseline_end=snapshot.planned_date,
                current_start=milestone.date,
                current_end=milestone.date,
                delta_start_days=(milestone.date - snapshot.planned_date).days,
                delta_end_days=(milestone.date - snapshot.planned_date).days,
            )
        )

    # Most-drifted first — the whole point of a comparison is to surface
    # what has moved, not to relist everything in its original order.
    items.sort(key=lambda i: abs(i.delta_end_days), reverse=True)

    return BaselineComparison(baseline=BaselineRead.model_validate(baseline), items=items)
