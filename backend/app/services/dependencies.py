from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.dependency import Dependency
from app.models.enums import SchedulableType
from app.models.milestone import Milestone
from app.schemas.dependency import DependencyCreate, DependencyRead

NodeKey = tuple[SchedulableType, int]


def _get_label(db: Session, entity_type: SchedulableType, entity_id: int) -> str:
    obj = (
        db.get(Activity, entity_id)
        if entity_type == SchedulableType.ACTIVITY
        else db.get(Milestone, entity_id)
    )
    if obj is None:
        raise HTTPException(
            status_code=404, detail=f"{entity_type.value} {entity_id} not found"
        )
    return obj.title


def _serialize(db: Session, dep: Dependency) -> DependencyRead:
    return DependencyRead(
        id=dep.id,
        predecessor_type=dep.predecessor_type,
        predecessor_id=dep.predecessor_id,
        predecessor_label=_get_label(db, dep.predecessor_type, dep.predecessor_id),
        successor_type=dep.successor_type,
        successor_id=dep.successor_id,
        successor_label=_get_label(db, dep.successor_type, dep.successor_id),
        dependency_type=dep.dependency_type,
        lag_days=dep.lag_days,
    )


def list_dependencies(db: Session) -> list[DependencyRead]:
    deps = db.scalars(select(Dependency)).all()
    return [_serialize(db, d) for d in deps]


def _would_create_cycle(
    db: Session,
    predecessor_type: SchedulableType,
    predecessor_id: int,
    successor_type: SchedulableType,
    successor_id: int,
) -> bool:
    """True if the successor can already reach the predecessor through
    existing edges — i.e. adding predecessor -> successor would close a loop."""
    edges = db.scalars(select(Dependency)).all()
    adjacency: dict[NodeKey, list[NodeKey]] = {}
    for e in edges:
        adjacency.setdefault((e.predecessor_type, e.predecessor_id), []).append(
            (e.successor_type, e.successor_id)
        )

    target: NodeKey = (predecessor_type, predecessor_id)
    start: NodeKey = (successor_type, successor_id)
    visited = {start}
    queue = [start]
    while queue:
        node = queue.pop()
        if node == target:
            return True
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return False


def create_dependency(db: Session, payload: DependencyCreate) -> DependencyRead:
    _get_label(db, payload.predecessor_type, payload.predecessor_id)
    _get_label(db, payload.successor_type, payload.successor_id)

    existing = db.scalars(
        select(Dependency).where(
            Dependency.predecessor_type == payload.predecessor_type,
            Dependency.predecessor_id == payload.predecessor_id,
            Dependency.successor_type == payload.successor_type,
            Dependency.successor_id == payload.successor_id,
        )
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="This dependency already exists")

    if _would_create_cycle(
        db,
        payload.predecessor_type,
        payload.predecessor_id,
        payload.successor_type,
        payload.successor_id,
    ):
        raise HTTPException(
            status_code=409,
            detail="This dependency would create a cycle in the schedule",
        )

    dependency = Dependency(
        predecessor_type=payload.predecessor_type,
        predecessor_id=payload.predecessor_id,
        successor_type=payload.successor_type,
        successor_id=payload.successor_id,
        dependency_type=payload.dependency_type,
        lag_days=payload.lag_days,
    )
    db.add(dependency)
    db.commit()
    db.refresh(dependency)
    return _serialize(db, dependency)


def delete_dependency(db: Session, dependency_id: int) -> None:
    dependency = db.get(Dependency, dependency_id)
    if dependency is None:
        raise HTTPException(status_code=404, detail="Dependency not found")
    db.delete(dependency)
    db.commit()
