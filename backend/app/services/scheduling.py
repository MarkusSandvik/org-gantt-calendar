import datetime as dt
import uuid
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import permissions
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.dependency import Dependency
from app.models.enums import SchedulableType
from app.models.milestone import Milestone
from app.models.user import User
from app.schemas.scheduling import (
    ScheduleChangeItem,
    SchedulingApplyResponse,
    SchedulingChangeRequest,
)

NodeKey = tuple[SchedulableType, int]
Edge = tuple[NodeKey, int]  # (successor_key, lag_days)


@dataclass(frozen=True)
class ScheduleNode:
    key: NodeKey
    start_date: dt.date
    end_date: dt.date


def compute_propagation(
    nodes: dict[NodeKey, ScheduleNode],
    adjacency: dict[NodeKey, list[Edge]],
    changed_key: NodeKey,
    new_start: dt.date,
    new_end: dt.date,
) -> dict[NodeKey, tuple[dt.date, dt.date]]:
    """Forward-only schedule propagation.

    A node whose end date moves later forces each successor's start (and,
    preserving its duration, its end) later too, honoring the dependency's
    lag. Dates never move earlier — a predecessor finishing sooner never
    pulls a successor forward — so on a DAG (cycles are rejected at write
    time) this queue-based relaxation always terminates: every update only
    ever increases a date, and there are finitely many edges to relax.

    Returns every node whose dates change, keyed the same as `nodes`,
    including the initiating `changed_key` itself.
    """
    working: dict[NodeKey, tuple[dt.date, dt.date]] = {
        key: (node.start_date, node.end_date) for key, node in nodes.items()
    }
    working[changed_key] = (new_start, new_end)
    changes: dict[NodeKey, tuple[dt.date, dt.date]] = {changed_key: (new_start, new_end)}

    queue: deque[NodeKey] = deque([changed_key])
    while queue:
        current = queue.popleft()
        _, current_end = working[current]
        for succ_key, lag_days in adjacency.get(current, []):
            if succ_key not in working:
                continue
            succ_start, succ_end = working[succ_key]
            required_start = current_end + dt.timedelta(days=lag_days)
            if required_start > succ_start:
                duration = succ_end - succ_start
                new_succ_start = required_start
                new_succ_end = new_succ_start + duration
                working[succ_key] = (new_succ_start, new_succ_end)
                changes[succ_key] = (new_succ_start, new_succ_end)
                queue.append(succ_key)

    return changes


def _load_graph(
    db: Session,
) -> tuple[dict[NodeKey, ScheduleNode], dict[NodeKey, list[Edge]], dict[NodeKey, str]]:
    nodes: dict[NodeKey, ScheduleNode] = {}
    labels: dict[NodeKey, str] = {}

    for activity in db.scalars(select(Activity)).all():
        key = (SchedulableType.ACTIVITY, activity.id)
        nodes[key] = ScheduleNode(key, activity.start_date, activity.end_date)
        labels[key] = activity.title

    for milestone in db.scalars(select(Milestone)).all():
        key = (SchedulableType.MILESTONE, milestone.id)
        nodes[key] = ScheduleNode(key, milestone.date, milestone.date)
        labels[key] = milestone.title

    adjacency: dict[NodeKey, list[Edge]] = {}
    for dep in db.scalars(select(Dependency)).all():
        pred_key = (dep.predecessor_type, dep.predecessor_id)
        succ_key = (dep.successor_type, dep.successor_id)
        adjacency.setdefault(pred_key, []).append((succ_key, dep.lag_days))

    return nodes, adjacency, labels


def _validate_request(payload: SchedulingChangeRequest) -> None:
    if payload.new_end_date < payload.new_start_date:
        raise HTTPException(status_code=422, detail="end_date must not be before start_date")
    if payload.entity_type == SchedulableType.MILESTONE and payload.new_start_date != payload.new_end_date:
        raise HTTPException(
            status_code=422,
            detail="A milestone has a single date; new_start_date and new_end_date must match",
        )


def _get_root_or_404(db: Session, entity_type: SchedulableType, entity_id: int) -> None:
    obj = (
        db.get(Activity, entity_id)
        if entity_type == SchedulableType.ACTIVITY
        else db.get(Milestone, entity_id)
    )
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{entity_type.value} {entity_id} not found")


def _build_change_items(
    changes: dict[NodeKey, tuple[dt.date, dt.date]],
    nodes: dict[NodeKey, ScheduleNode],
    labels: dict[NodeKey, str],
) -> list[ScheduleChangeItem]:
    items: list[ScheduleChangeItem] = []
    for key, (new_start, new_end) in changes.items():
        old_start, old_end = nodes[key].start_date, nodes[key].end_date
        if (new_start, new_end) == (old_start, old_end):
            continue
        items.append(
            ScheduleChangeItem(
                entity_type=key[0],
                entity_id=key[1],
                label=labels[key],
                old_start_date=old_start,
                old_end_date=old_end,
                new_start_date=new_start,
                new_end_date=new_end,
                delta_days=(new_start - old_start).days,
            )
        )
    items.sort(key=lambda i: (i.entity_type.value, i.entity_id))
    return items


def _entity_team_id(db: Session, entity_type: SchedulableType, entity_id: int) -> int | None:
    return permissions.schedulable_team_id(db, entity_type.value, entity_id)


def _authorize_schedule_items(
    db: Session, user: User, entities: list[tuple[SchedulableType, int]]
) -> None:
    """Admin may apply/undo anything. A Lead may only touch entities that
    belong to their own team — an org-wide milestone (team_id is None)
    counts as belonging to no team a Lead can claim. Rather than silently
    applying the in-team part and dropping the rest, a change that reaches
    outside the Lead's team is rejected outright with the full list of
    what it would have touched, so nothing is applied halfway (Section 7:
    'do NOT silently apply those external changes')."""
    if permissions.is_admin(user):
        return

    led_team_id = permissions.get_led_team_id(db, user)
    if led_team_id is None:
        raise HTTPException(
            status_code=403, detail="Only a team Lead or Admin can change the schedule."
        )

    external = [
        {"entity_type": entity_type.value, "entity_id": entity_id}
        for entity_type, entity_id in entities
        if _entity_team_id(db, entity_type, entity_id) != led_team_id
    ]
    if external:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "This change affects another team's schedule (or an "
                    "organization-wide milestone) and requires Admin approval."
                ),
                "external_items": external,
            },
        )


def preview_schedule_change(
    db: Session, payload: SchedulingChangeRequest, user: User
) -> list[ScheduleChangeItem]:
    if not permissions.is_admin(user) and permissions.get_led_team_id(db, user) is None:
        raise HTTPException(
            status_code=403, detail="Only a team Lead or Admin can preview scheduling changes."
        )
    _validate_request(payload)
    _get_root_or_404(db, payload.entity_type, payload.entity_id)

    nodes, adjacency, labels = _load_graph(db)
    changed_key = (payload.entity_type, payload.entity_id)
    changes = compute_propagation(
        nodes, adjacency, changed_key, payload.new_start_date, payload.new_end_date
    )
    return _build_change_items(changes, nodes, labels)


def apply_schedule_change(
    db: Session, payload: SchedulingChangeRequest, user: User
) -> SchedulingApplyResponse:
    _validate_request(payload)
    _get_root_or_404(db, payload.entity_type, payload.entity_id)

    nodes, adjacency, labels = _load_graph(db)
    changed_key = (payload.entity_type, payload.entity_id)
    changes = compute_propagation(
        nodes, adjacency, changed_key, payload.new_start_date, payload.new_end_date
    )
    items = _build_change_items(changes, nodes, labels)

    if not items:
        return SchedulingApplyResponse(change_group_id="", changes=[])

    _authorize_schedule_items(db, user, [(item.entity_type, item.entity_id) for item in items])

    user_id = user.id
    change_group_id = uuid.uuid4().hex
    for item in items:
        if item.entity_type == SchedulableType.ACTIVITY:
            activity = db.get(Activity, item.entity_id)
            assert activity is not None
            activity.start_date = item.new_start_date
            activity.end_date = item.new_end_date
            db.add(
                AuditLog(
                    entity_type="activity",
                    entity_id=item.entity_id,
                    user_id=user_id,
                    field_name="start_date",
                    old_value=str(item.old_start_date),
                    new_value=str(item.new_start_date),
                    reason=payload.reason,
                    change_group_id=change_group_id,
                )
            )
            db.add(
                AuditLog(
                    entity_type="activity",
                    entity_id=item.entity_id,
                    user_id=user_id,
                    field_name="end_date",
                    old_value=str(item.old_end_date),
                    new_value=str(item.new_end_date),
                    reason=payload.reason,
                    change_group_id=change_group_id,
                )
            )
        else:
            milestone = db.get(Milestone, item.entity_id)
            assert milestone is not None
            milestone.date = item.new_start_date
            db.add(
                AuditLog(
                    entity_type="milestone",
                    entity_id=item.entity_id,
                    user_id=user_id,
                    field_name="date",
                    old_value=str(item.old_start_date),
                    new_value=str(item.new_start_date),
                    reason=payload.reason,
                    change_group_id=change_group_id,
                )
            )

    db.commit()
    return SchedulingApplyResponse(change_group_id=change_group_id, changes=items)


def undo_schedule_change(
    db: Session, change_group_id: str, user: User
) -> list[ScheduleChangeItem]:
    logs = db.scalars(
        select(AuditLog).where(AuditLog.change_group_id == change_group_id)
    ).all()
    if not logs:
        raise HTTPException(status_code=404, detail="No scheduling change found with that id")

    by_entity: dict[tuple[str, int], list[AuditLog]] = {}
    for log in logs:
        by_entity.setdefault((log.entity_type, log.entity_id), []).append(log)

    _authorize_schedule_items(
        db,
        user,
        [(SchedulableType(entity_type), entity_id) for entity_type, entity_id in by_entity],
    )

    user_id = user.id
    undo_group_id = uuid.uuid4().hex
    reverted_items: list[ScheduleChangeItem] = []

    for (entity_type, entity_id), entity_logs in by_entity.items():
        if entity_type == "activity":
            activity = db.get(Activity, entity_id)
            if activity is None:
                continue
            old_start, old_end = activity.start_date, activity.end_date
            for log in entity_logs:
                restored = dt.date.fromisoformat(log.old_value)
                if log.field_name == "start_date":
                    activity.start_date = restored
                elif log.field_name == "end_date":
                    activity.end_date = restored
                db.add(
                    AuditLog(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        user_id=user_id,
                        field_name=log.field_name,
                        old_value=log.new_value,
                        new_value=log.old_value,
                        reason="Undo scheduling change",
                        change_group_id=undo_group_id,
                    )
                )
            reverted_items.append(
                ScheduleChangeItem(
                    entity_type=SchedulableType.ACTIVITY,
                    entity_id=entity_id,
                    label=activity.title,
                    old_start_date=old_start,
                    old_end_date=old_end,
                    new_start_date=activity.start_date,
                    new_end_date=activity.end_date,
                    delta_days=(activity.start_date - old_start).days,
                )
            )
        else:
            milestone = db.get(Milestone, entity_id)
            if milestone is None:
                continue
            old_date = milestone.date
            for log in entity_logs:
                restored = dt.date.fromisoformat(log.old_value)
                milestone.date = restored
                db.add(
                    AuditLog(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        user_id=user_id,
                        field_name=log.field_name,
                        old_value=log.new_value,
                        new_value=log.old_value,
                        reason="Undo scheduling change",
                        change_group_id=undo_group_id,
                    )
                )
            reverted_items.append(
                ScheduleChangeItem(
                    entity_type=SchedulableType.MILESTONE,
                    entity_id=entity_id,
                    label=milestone.title,
                    old_start_date=old_date,
                    old_end_date=old_date,
                    new_start_date=milestone.date,
                    new_end_date=milestone.date,
                    delta_days=(milestone.date - old_date).days,
                )
            )

    db.commit()
    reverted_items.sort(key=lambda i: (i.entity_type.value, i.entity_id))
    return reverted_items
