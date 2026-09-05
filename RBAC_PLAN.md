# RBAC / Authentication — Migration Plan

Approved architecture plan for adding real authentication and Admin/Lead/Member
authorization on top of the existing v0.1 application. This document is the
durable record of the assessment; implementation proceeds phase by phase
against it. See `AUTHORIZATION.md` (added in Phase 4) for the live permission
matrix once the permission layer exists.

## Access model

- **Admin** — global, unrestricted. Not scoped to any team.
- **Lead** — organization-wide *view*, management authority only within the
  one team they lead (`TeamMembership.team_role == LEAD`).
- **Member** — organization-wide *view*, can edit progress/status/comments
  only on activities/milestones where they are owner or contributor.

## Schema changes

- `users`: add `password_hash`, `status` (`PENDING|ACTIVE|INACTIVE|ARCHIVED`,
  replacing `active: bool`), repurpose `role` → `global_role`
  (`USER|ADMIN`, replacing the unused `viewer/editor/admin` enum), add
  `last_login_at`.
- `team_memberships`: add `team_role` (`MEMBER|LEAD`), unique
  `(team_id, user_id)`. "At most one LEAD membership per user" enforced in
  the service layer, not a DB constraint, so it can be relaxed later.
- New `invitations`: `id, email, name, team_id (nullable), target_global_role,
  target_team_role (nullable), invited_by_user_id, token_hash, status
  (PENDING|ACCEPTED|REVOKED|EXPIRED), expires_at, created_at, accepted_at`.
- New `password_reset_tokens`: `id, user_id, token_hash, expires_at, used_at,
  created_at`.
- New `auth_sessions`: `id, user_id, token_hash, created_at, expires_at,
  revoked_at, user_agent`.

All via Alembic batch-mode migrations (existing project convention).

## Authentication

- HttpOnly, `SameSite=Lax` session cookie backed by `auth_sessions` (hash of
  token stored, never the raw token) — chosen over JWT because this is a
  single monolith API and instant revocation (logout, deactivate-while-
  logged-in) is a hard requirement; a stateless JWT would need a denylist to
  get the same property.
- Argon2id password hashing (`argon2-cffi`).
- Invitation and password-reset tokens: `secrets.token_urlsafe(32)`, only the
  SHA-256 hash persisted, single-use, time-limited.
- CSRF: double-submit cookie/header pair, checked on mutating requests.
- Generic login failure message for both unknown-email and wrong-password
  (no user enumeration).
- In-memory sliding-window rate limiter on login attempts, behind a small
  interface so a Redis-backed one can replace it later without call-site
  changes.

## Centralized authorization

`app/core/permissions.py::require(user, permission, resource=None, db=None)`
dispatches to small resolver functions keyed by `global_role` +
`team_memberships` + the resource being acted on. Routers call `require(...)`
before delegating to the existing service functions; services are not
rewritten, just gated.

## Permission matrix (summary — full matrix lives in AUTHORIZATION.md)

| Resource | Action | Member | Lead (own group) | Lead (other group) | Admin |
|---|---|---|---|---|---|
| Activity/Milestone | View | Yes | Yes | Yes | Yes |
| Activity | Create/Edit schedule/Delete | No | Yes | No | Yes |
| Activity | Edit progress/status | Assigned only | Yes | No | Yes |
| Comment | Create | Assigned only | Yes (own group) | No | Yes |
| Milestone | Manage (team-scoped) | No | Yes (matching team) | No | Yes |
| Milestone | Manage (org-wide, no team) | No | No | No | Yes |
| Dependency | Reference another group's task | No | Yes (as predecessor/successor id only) | — | Yes |
| Scheduling | Apply reaching another group | No | Blocked (409 + impact report) | No | Yes |
| Baseline / Team / Settings | Manage | No | No | No | Yes |
| User | Invite Member (own group) | No | Yes | — | Yes |
| User | Invite Lead/Admin | No | No | No | Yes |
| User | Change role / move team / deactivate | No | Deactivate own-group Member only | No | Yes |

## Implementation phases

1. Migration plan (this document). **Done.**
2. Schema: enums, models, Alembic migrations, seed data.
3. Authentication: hashing, sessions, login/logout/me, password reset.
4. Centralized authorization layer + `AUTHORIZATION.md`.
5. Protect existing endpoints (including the ones with zero identity
   resolution today: activity delete, calendar-events CRUD, dependency
   create/delete, milestone create/delete).
6. Invitations (create/list/revoke/accept).
7. User-management API (list/deactivate/reactivate/change team/promote/demote).
8. Login + user-management frontend.
9. Permission-aware UI across Gantt/activity/calendar/milestone/admin.
10. Audit events for every security-sensitive action.
11. Automated authorization tests (Member/Lead/Admin/security matrices).
12. Documentation pass (README, CHANGELOG, `.env.example`).

## Known risks / deliberate scope decisions

- The existing "Acting as" impersonation switcher is removed, replaced by
  real login/logout — it's a security hole once passwords exist and wasn't
  requested as a feature to keep.
- Cross-team scheduling **blocking** is implemented in full in Phase 5; a
  persisted pending-approval object with an Admin approve/reject UI is
  scoped as an optional follow-up (Phase 7b), not part of this pass.
- Organization-wide milestones (`team_id IS NULL`) are Admin-only to manage;
  no separate "Admin policy" toggle is introduced.
- ~100 existing backend tests assumed the old header-based mock auth; the
  `client` test fixture is updated to log in as a seeded Admin by default so
  they keep passing without individual edits.
- "Failed privileged action" (Section 17's one *optional* — "if
  appropriate" — audit event) is deliberately not implemented. A global
  exception handler for `PermissionDenied` would need its own DB session
  outside the request's `Depends(get_db)` — bypassing the test suite's
  in-memory-SQLite override and writing to whatever `DATABASE_URL`
  happens to be configured, silently breaking test isolation. Every other
  Section 17 event (invite, revoke, activate, deactivate, role change,
  membership add/remove, password reset) is implemented and tested in
  `tests/test_audit_events.py`; a real deployment's access/error logs
  already capture every denied request via its 403 response.
