from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.milestone import Milestone
from app.models.tag import Tag
from app.models.team import Team
from app.models.user import User
from app.schemas.search import SearchResult

RESULTS_PER_TYPE = 8


def global_search(
    db: Session, q: str, project_id: int | None = None
) -> list[SearchResult]:
    if not q or len(q.strip()) < 2:
        return []
    pattern = f"%{q.strip()}%"
    results: list[SearchResult] = []

    activity_stmt = select(Activity).where(Activity.title.ilike(pattern))
    if project_id is not None:
        activity_stmt = activity_stmt.where(Activity.project_id == project_id)
    activities = db.scalars(activity_stmt.order_by(Activity.title).limit(RESULTS_PER_TYPE)).all()
    for a in activities:
        results.append(
            SearchResult(
                type="activity",
                id=a.id,
                label=a.title,
                subtitle=a.status.value.replace("_", " "),
            )
        )

    milestone_stmt = select(Milestone).where(Milestone.title.ilike(pattern))
    if project_id is not None:
        milestone_stmt = milestone_stmt.where(Milestone.project_id == project_id)
    milestones = db.scalars(
        milestone_stmt.order_by(Milestone.title).limit(RESULTS_PER_TYPE)
    ).all()
    for m in milestones:
        results.append(
            SearchResult(type="milestone", id=m.id, label=m.title, subtitle=str(m.date))
        )

    team_stmt = select(Team).where(Team.name.ilike(pattern), Team.archived_at.is_(None))
    if project_id is not None:
        team_stmt = team_stmt.where(Team.project_id == project_id)
    teams = db.scalars(team_stmt.order_by(Team.name).limit(RESULTS_PER_TYPE)).all()
    for t in teams:
        results.append(
            SearchResult(type="team", id=t.id, label=t.name, subtitle=t.category.value)
        )

    tag_stmt = select(Tag).where(Tag.name.ilike(pattern), Tag.archived_at.is_(None))
    if project_id is not None:
        tag_stmt = tag_stmt.where(Tag.project_id == project_id)
    tags = db.scalars(tag_stmt.order_by(Tag.name).limit(RESULTS_PER_TYPE)).all()
    for tag in tags:
        results.append(SearchResult(type="tag", id=tag.id, label=tag.name))

    user_stmt = (
        select(User)
        .where(User.name.ilike(pattern), User.active.is_(True))
        .order_by(User.name)
        .limit(RESULTS_PER_TYPE)
    )
    users = db.scalars(user_stmt).all()
    for u in users:
        results.append(SearchResult(type="user", id=u.id, label=u.name, subtitle=u.role.value))

    return results
