"""Centralized authorization. Every permission decision in the app should
go through `require()` (or one of the small resource-specific helpers
below it) rather than an ad hoc `if user.role == ...` scattered in a
router or service — see RBAC_PLAN.md / AUTHORIZATION.md for the approved
model this implements.

The three roles this resolves against:
  - Admin (User.global_role == ADMIN): unrestricted, every check below
    short-circuits to True before looking at anything else.
  - Lead (a TeamMembership row with team_role == LEAD): management
    authority scoped to that one team. A user can lead at most one team
    (enforced in services/team_membership.py, not here).
  - Member: everyone else. Organization-wide view, edit rights only on
    activities/milestones they are assigned to as owner or contributor.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity, ActivityContributor
from app.models.calendar_event import CalendarEvent
from app.models.enums import GlobalRole, TeamRole
from app.models.milestone import Milestone
from app.models.team import TeamMembership
from app.models.user import User


class PermissionDenied(HTTPException):
    def __init__(self, detail: str = "You don't have permission to do that.") -> None:
        super().__init__(status_code=403, detail=detail)


def is_admin(user: User) -> bool:
    return user.global_role == GlobalRole.ADMIN


def get_led_team_id(db: Session, user: User) -> int | None:
    """The single team this user leads, or None. A user may lead at most
    one team in the current model (see TeamMembership) — this returns the
    first match, which is also the only one that should ever exist."""
    return db.scalars(
        select(TeamMembership.team_id).where(
            TeamMembership.user_id == user.id, TeamMembership.team_role == TeamRole.LEAD
        )
    ).first()


def is_member_of_team(db: Session, user: User, team_id: int | None) -> bool:
    if team_id is None:
        return False
    return (
        db.scalars(
            select(TeamMembership.id).where(
                TeamMembership.user_id == user.id, TeamMembership.team_id == team_id
            )
        ).first()
        is not None
    )


def leads_team(db: Session, user: User, team_id: int | None) -> bool:
    if team_id is None:
        return False
    return get_led_team_id(db, user) == team_id


def is_assigned_to_activity(db: Session, user: User, activity: Activity) -> bool:
    if activity.owner_user_id == user.id:
        return True
    return (
        db.scalars(
            select(ActivityContributor.id).where(
                ActivityContributor.activity_id == activity.id,
                ActivityContributor.user_id == user.id,
            )
        ).first()
        is not None
    )


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

# Fields a Member may change on an activity they're assigned to. Everything
# else (dates, priority, owner, contributors, team, title, description) is
# Lead/Admin-only — see the ActivityUpdate schema for the full field set.
MEMBER_EDITABLE_ACTIVITY_FIELDS = {"status", "progress_percent"}


def can_create_activity(db: Session, user: User, team_id: int | None) -> bool:
    if is_admin(user):
        return True
    return leads_team(db, user, team_id)


def can_edit_activity(db: Session, user: User, activity: Activity) -> bool:
    """Full edit rights (schedule, priority, owner, contributors, team,
    delete) — Admin or the Lead of the activity's own team only."""
    if is_admin(user):
        return True
    return leads_team(db, user, activity.owner_team_id)


def can_update_activity_fields(
    db: Session, user: User, activity: Activity, changed_fields: set[str]
) -> bool:
    """Members may update only status/progress_percent, and only on an
    activity they're assigned to. Any other changed field requires full
    edit rights (Lead of the activity's team, or Admin)."""
    if is_admin(user):
        return True
    if leads_team(db, user, activity.owner_team_id):
        return True
    if changed_fields - MEMBER_EDITABLE_ACTIVITY_FIELDS:
        return False
    return is_assigned_to_activity(db, user, activity)


def can_delete_activity(db: Session, user: User, activity: Activity) -> bool:
    return can_edit_activity(db, user, activity)


def can_comment_on_activity(db: Session, user: User, activity: Activity) -> bool:
    if is_admin(user):
        return True
    if leads_team(db, user, activity.owner_team_id):
        return True
    return is_assigned_to_activity(db, user, activity)


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------


def can_manage_milestone_for_team(db: Session, user: User, team_id: int | None) -> bool:
    """Organization-wide milestones (team_id is None) are Admin-only — see
    RBAC_PLAN.md's note on Section 1's 'unless explicitly allowed by Admin
    policy' hedge; no such policy toggle exists, so the safe default wins."""
    if is_admin(user):
        return True
    return leads_team(db, user, team_id)


def can_manage_milestone(db: Session, user: User, milestone: Milestone) -> bool:
    return can_manage_milestone_for_team(db, user, milestone.team_id)


def can_comment_on_milestone(db: Session, user: User, milestone: Milestone) -> bool:
    if is_admin(user):
        return True
    if leads_team(db, user, milestone.team_id):
        return True
    return milestone.owner_user_id == user.id


# ---------------------------------------------------------------------------
# Calendar events
# ---------------------------------------------------------------------------


def can_manage_calendar_event_for_team(db: Session, user: User, team_id: int | None) -> bool:
    if is_admin(user):
        return True
    return leads_team(db, user, team_id)


def can_manage_calendar_event(db: Session, user: User, event: CalendarEvent) -> bool:
    return can_manage_calendar_event_for_team(db, user, event.team_id)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def schedulable_team_id(db: Session, entity_type: str, entity_id: int) -> int | None:
    if entity_type == "activity":
        activity = db.get(Activity, entity_id)
        return activity.owner_team_id if activity else None
    milestone = db.get(Milestone, entity_id)
    return milestone.team_id if milestone else None


def can_manage_dependency(
    db: Session,
    user: User,
    predecessor_type: str,
    predecessor_id: int,
    successor_type: str,
    successor_id: int,
) -> bool:
    """A Lead may reference another team's task as either end of a
    dependency, as long as their own team owns at least one end — this
    grants no edit rights over the other team's task (see Section 7)."""
    if is_admin(user):
        return True
    led_team_id = get_led_team_id(db, user)
    if led_team_id is None:
        return False
    predecessor_team = schedulable_team_id(db, predecessor_type, predecessor_id)
    successor_team = schedulable_team_id(db, successor_type, successor_id)
    return led_team_id in (predecessor_team, successor_team)


# ---------------------------------------------------------------------------
# Baselines / Teams / Settings — Admin-only, no scoping to check
# ---------------------------------------------------------------------------


def can_manage_baseline(user: User) -> bool:
    return is_admin(user)


def can_manage_team(user: User) -> bool:
    return is_admin(user)


def can_manage_settings(user: User) -> bool:
    return is_admin(user)


# ---------------------------------------------------------------------------
# Users / invitations — scope derivation lives in services/invitations.py
# and services/user_admin.py (Phases 6/7); these are the coarse gates.
# ---------------------------------------------------------------------------


def can_deactivate_user(db: Session, actor: User, target: User) -> bool:
    if is_admin(actor):
        return True
    led_team_id = get_led_team_id(db, actor)
    if led_team_id is None or target.global_role == GlobalRole.ADMIN:
        return False
    target_team_ids = db.scalars(
        select(TeamMembership.team_id).where(
            TeamMembership.user_id == target.id, TeamMembership.team_role == TeamRole.MEMBER
        )
    ).all()
    return led_team_id in target_team_ids


def require(condition: bool, detail: str = "You don't have permission to do that.") -> None:
    """Thin, deliberately boring wrapper — every mutation's authorization
    check should read as `permissions.require(permissions.can_x(...))`, one
    line, at the top of the router or service function, rather than a
    bespoke if/raise. Keeping this trivial is the point: the actual
    decisions live in the named `can_*` functions above, not here."""
    if not condition:
        raise PermissionDenied(detail)
