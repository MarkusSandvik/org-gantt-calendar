# Changelog

## Phase 2 — Activity CRUD (2026-09-04)

Full create/read/update/delete for activities, plus the supporting pieces
needed to make that usable: a mocked-auth "acting as" user identity, and
read-only Users/Tags endpoints to populate selects.

**Backend**
- `X-User-Id` header dependency (`app/core/deps.py`) resolves the acting
  user for `created_by` attribution; falls back to the first user if the
  header is omitted, so the API stays usable without it (e.g. via `/docs`).
- `GET /users`, `GET /tags` (read-only; full admin CRUD for these follows in
  a later phase — added now only because the Activity form's owner/
  contributor/tag selects need them).
- `GET/POST/PATCH/DELETE /activities` with filters (`project_id`, `team_id`,
  `owner_user_id`, `status`, `priority`, `q`). Business logic lives in
  `app/services/activities.py`, not the router: date-order and progress-range
  validation, 404s for unknown team/user/tag references, and a 409 guard
  that blocks deleting an activity with existing dependencies (dependencies
  themselves arrive in Phase 5, but the guard is in place now so it isn't
  forgotten later).
- Contributors and tags are synced from plain id lists in the request body
  (`contributor_user_ids`, `tag_ids`) rather than separate sub-resource
  endpoints — simpler for v0.1's single-admin-form UI.
- 13 pytest cases covering create/list/get/update/delete, partial-update
  semantics (`PATCH` only touches fields actually sent), date/progress
  validation, and the dependency-delete guard.

**Frontend**
- "Acting as" user switcher in the app shell top bar (Zustand store,
  persisted to localStorage), defaults to the first seeded user and sends
  `X-User-Id` on every mutating request via the extended API client
  (`post`/`patch`/`delete`).
- Admin is now a nested layout (`/admin/activities`, with placeholder tabs
  for Teams/Tags/Users/Dependencies/Baselines/Import-Export/Settings naming
  the phase each arrives in) instead of a single flat page.
- Activities admin: filterable table (team, status, priority, title search)
  and a single create/edit modal form covering all activity fields,
  including checkbox multi-selects for contributors and tags. `StatusBadge`
  and `PriorityBadge` components introduced here will be reused by the
  Gantt and Dashboard later.

**Verified:** backend tests pass (13/13), frontend type-checks clean,
full create → list/filter → edit → delete flow exercised in a real browser
against the running backend (delete verified via direct API call to avoid
the native `confirm()` dialog blocking browser automation — the in-app
delete button itself is unchanged and works normally for a human user).

**Not yet implemented:** Teams/Tags/Users admin CRUD (currently read-only,
supporting the Activity form only), Dependencies, Gantt rendering, and
everything else on the Phase 3+ list below.

## Phase 1 — Project skeleton and database (2026-09-04)

Establishes the runnable foundation for all later phases.

**Backend**
- FastAPI app with CORS, `/api/v1/health`, read-only `/api/v1/projects` and
  `/api/v1/teams` endpoints (smoke-test only; full CRUD arrives in Phase 2).
- SQLAlchemy 2.0 models for all 17 entities from the architecture proposal:
  Project, User, Team, TeamMembership, Tag, TagAssociation, Activity,
  ActivityContributor, Dependency, Milestone, CalendarEvent, Comment,
  Attachment, Baseline, BaselineActivity, BaselineMilestone, AuditLog.
  Tags and comments use a polymorphic `entity_type`/`entity_id` pattern so a
  single table serves activities, milestones, and calendar events. Dependency
  endpoints are similarly polymorphic (activity or milestone) so both kinds
  of schedulable object can depend on each other later.
- Alembic configured with batch mode (`render_as_batch=True`) so future
  migrations stay compatible with SQLite's limited `ALTER TABLE` support and
  with an eventual PostgreSQL target. Initial migration generated and applied.
- Idempotent seed script (`app/db/seed.py`) populating one demo project
  ("AUV 2026"), all 11 teams, all 12 tags, 5 demo users, 9 activities
  (including a dependency chain and delayed/blocked examples), 4 milestones,
  and a sample week of calendar events.
- Pytest suite with an isolated in-memory SQLite fixture per test.

**Frontend**
- Vite + React 19 + TypeScript app shell with React Router, TanStack Query,
  and Zustand installed (Zustand not yet used — no local UI state to manage
  until filters/selection land in a later phase).
- Nav sidebar with all six top-level sections (Dashboard, Gantt, Calendar,
  Milestones, My Tasks, Admin); each non-Dashboard page is a placeholder
  naming the phase it arrives in.
- Dashboard and Admin pages make live API calls (via a typed `api/client.ts`
  fetch wrapper) to prove frontend-backend wiring end-to-end; verified in
  browser against the seeded data.
- Dev server proxies `/api/*` to the backend (`vite.config.ts`), so no env
  vars are needed for local development.

**Verified:** backend tests pass, `alembic upgrade head` runs clean from an
empty database, seed script populates correctly, frontend type-checks with
no errors, and the running app was checked in a browser end-to-end.

**Not yet implemented** (by design — later phases): Activity/Milestone/Team/
Tag CRUD and admin forms, Gantt rendering, dependency validation and
visualization, the scheduling engine, calendar UI, baselines, audit history
UI, import/export, and the My Tasks view.
