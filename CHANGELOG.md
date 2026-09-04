# Changelog

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
