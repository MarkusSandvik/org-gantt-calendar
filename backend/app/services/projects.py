import datetime as dt
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.models.tag import Tag
from app.models.team import Team, TeamMembership
from app.schemas.project import ProjectCreate, ProjectUpdate


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


# The frontend router treats a first URL segment matching one of these as
# the old flat route (e.g. "/gantt"), never as a project slug — see
# LEGACY_PROJECT_PATHS in App.tsx. A project slug equal to one of these
# would be permanently unreachable, so it's excluded here at the source.
RESERVED_SLUGS = {
    "gantt",
    "calendar",
    "milestones",
    "my-tasks",
    "admin",
    "login",
    "accept-invitation",
    "reset-password",
}


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    suffix = 2
    while (
        slug in RESERVED_SLUGS
        or db.scalars(select(Project.id).where(Project.slug == slug)).first() is not None
    ):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())


def get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


_EDITABLE_STATUSES = {ProjectStatus.DRAFT, ProjectStatus.ACTIVE}


def ensure_project_editable(db: Session, project_id: int) -> None:
    """Raises 422 if the project is COMPLETED or ARCHIVED. Every service that
    creates, updates, or deletes a project-scoped entity must call this
    before writing, so history stays read-only regardless of what the
    frontend does or doesn't disable."""
    project = get_project(db, project_id)
    if project.status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"'{project.name}' is {project.status.value} and read-only.",
        )


def _copy_structure(db: Session, source_project_id: int, target_project_id: int) -> None:
    """Duplicates a project's Teams and Tags (structure only) into a new
    project. Deliberately excludes activities, milestones, calendar events,
    dependencies, and baselines — a new season starts with an empty
    schedule, not last season's dates. Team memberships are excluded too,
    *except* for a team flagged `auto_transfer_membership` (Board/Admin,
    typically): those hold shared, role-based accounts rather than a
    personally recruited roster, so their membership always carries over.
    Every other team's roster is a deliberate choice made afterward, one
    member at a time, via the ordinary team-membership endpoint — this
    function never guesses at it."""
    source_teams = db.scalars(
        select(Team).where(Team.project_id == source_project_id, Team.archived_at.is_(None))
    ).all()
    for team in source_teams:
        new_team = Team(
            project_id=target_project_id,
            name=team.name,
            category=team.category,
            color=team.color,
            sort_order=team.sort_order,
            auto_transfer_membership=team.auto_transfer_membership,
        )
        db.add(new_team)
        if team.auto_transfer_membership:
            db.flush()  # assigns new_team.id
            memberships = db.scalars(
                select(TeamMembership).where(TeamMembership.team_id == team.id)
            ).all()
            for membership in memberships:
                db.add(
                    TeamMembership(
                        team_id=new_team.id,
                        user_id=membership.user_id,
                        team_role=membership.team_role,
                    )
                )

    source_tags = db.scalars(
        select(Tag).where(Tag.project_id == source_project_id, Tag.archived_at.is_(None))
    ).all()
    for tag in source_tags:
        db.add(Tag(project_id=target_project_id, name=tag.name, color=tag.color))


def create_project(db: Session, payload: ProjectCreate, created_by_id: int) -> Project:
    if payload.copy_structure_from_project_id is not None:
        get_project(db, payload.copy_structure_from_project_id)  # 404s if missing

    base_slug = _slugify(payload.slug or payload.name)
    slug = _unique_slug(db, base_slug)
    project = Project(
        name=payload.name,
        slug=slug,
        season_label=payload.season_label,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=ProjectStatus.DRAFT,
        is_default=False,
        created_by_id=created_by_id,
    )
    db.add(project)
    db.flush()

    if payload.copy_structure_from_project_id is not None:
        _copy_structure(db, payload.copy_structure_from_project_id, project.id)

    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project_id: int, payload: ProjectUpdate) -> Project:
    """Edits a project's own name/season/description/dates. Gated by the
    same read-only rule as everything else it contains — a completed or
    archived project's own record is frozen too, not just its activities
    and milestones."""
    project = get_project(db, project_id)
    ensure_project_editable(db, project_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


# A project starts in DRAFT while an Admin configures it, becomes ACTIVE for
# day-to-day work, is marked COMPLETED when the season ends, and ARCHIVED
# once it's pure history. ARCHIVED is deliberately a dead end here — nothing
# auto-unarchives; see Section 16 of the design doc for the (not yet
# implemented) explicit Admin-unlock flow this leaves room for.
_VALID_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.DRAFT: {ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED},
    ProjectStatus.ACTIVE: {ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED},
    ProjectStatus.COMPLETED: {ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED},
    ProjectStatus.ARCHIVED: set(),
}


def set_project_status(db: Session, project_id: int, new_status: ProjectStatus) -> Project:
    """Performs the mechanical status transition only — the confirmation
    ("this will complete Team 27") is the caller's (frontend's)
    responsibility; this function never transitions silently on its own."""
    project = get_project(db, project_id)
    if new_status == project.status:
        return project
    if new_status not in _VALID_TRANSITIONS[project.status]:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot move a project from {project.status.value} to {new_status.value}.",
        )

    if new_status == ProjectStatus.ACTIVE:
        # Exactly one project is "the" default (what "/" lands everyone on)
        # at a time — activating this one demotes whichever project held
        # that spot before. It deliberately does NOT complete that project:
        # a leadership handover often means two seasons are genuinely
        # active in parallel for a while (next season's Board is elected
        # and its teams staffed before this season's work is finished), so
        # completing the outgoing project stays a separate, explicit action
        # an Admin takes only once that handover is actually done.
        previous_default = db.scalars(
            select(Project).where(Project.is_default.is_(True), Project.id != project.id)
        ).first()
        if previous_default is not None:
            previous_default.is_default = False
        project.is_default = True

    project.status = new_status
    if new_status == ProjectStatus.ARCHIVED:
        project.archived_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)
        project.is_default = False

    db.commit()
    db.refresh(project)
    return project
