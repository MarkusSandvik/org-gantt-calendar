# Org Gantt & Calendar

Local-first project planning and organization management system: Gantt chart,
calendar/week view, dashboard, and admin tools for an organization's
technical and organizational activities. The core is generic and reusable —
a single deployment serves one organization, selected at startup by an
environment variable — see **Architecture** below.

See the full architecture proposal, database model, scheduling engine design,
and phased implementation plan discussed with the project owner before
implementation began (development phases are tracked in `CHANGELOG.md`).
Role-based access control (Admin/Lead/Member) was added after v0.1 shipped —
see `RBAC_PLAN.md` for that architecture and `AUTHORIZATION.md` for the live
permission matrix. The organization abstraction (this file's **Architecture**
section) was added afterward — see `ORGANIZATION_PLAN.md` for that design.

## Stack

- **Frontend:** React 19 + TypeScript, Vite, React Router, TanStack Query
- **Backend:** FastAPI, SQLAlchemy 2.0 (typed ORM), Alembic (migrations), Pydantic v2, Argon2 password hashing
- **Database:** SQLite locally (`backend/data/app.db`), PostgreSQL in later deployment

## Project layout

```
backend/
  app/
    core/       settings, organization profile loader (organization.py)
    organizations/  one subpackage per org: config.py (branding) + seed_data.py
    extensions/     optional org-specific backend features (empty by default)
    db/         engine/session, declarative base, generic seed engine
    models/     SQLAlchemy ORM models (one file per entity)
    schemas/    Pydantic request/response schemas
    routers/    FastAPI route handlers
    services/   business logic (scheduling engine lands here in a later phase)
    repositories/  data-access layer (introduced as CRUD grows)
  alembic/      migrations (batch mode enabled for SQLite ALTER TABLE support)
  tests/        pytest suite (in-memory SQLite per test)
frontend/
  src/
    api/        typed fetch client + response types
    branding/   one profile per org: product name, favicon, feature flags
    extensions/ optional org-specific frontend features (empty by default)
    components/layout/   app shell, nav, shared placeholders
    pages/      one file per top-level view (Dashboard, Gantt, Calendar, ...)
```

## Architecture

The app is split into three layers, so one codebase can serve any
organization without forking:

- **Core** (everything not listed below) — generic, reusable functionality:
  scheduling, Gantt/calendar rendering, RBAC, the data model. Core never
  branches on an organization or team's *name*, only on IDs and roles (see
  `AUTHORIZATION.md`) — this is what lets the same code serve every
  deployment.
- **Organization configuration** — `backend/app/organizations/<id>/` and
  `frontend/src/branding/profiles/<id>.ts`. Each profile supplies branding
  (product name, favicon), a static `features` flag dict, and (backend only)
  the demo/seed data for that org. Which profile is active is chosen once,
  at process start (backend) or build time (frontend), by the
  `APP_ORGANIZATION` / `VITE_ORGANIZATION` environment variables — both
  default to `"default"`, the neutral example organization shipped in this
  repo, so a fresh clone runs with zero configuration.
- **Organization-specific extensions** — `backend/app/extensions/` and
  `frontend/src/extensions/`, empty until a real one is needed (see the
  `README.md` in each). An extension is gated by a feature flag in the
  active profile; core never imports a specific extension by name.

This is deliberately **not** multi-tenant SaaS: one running deployment
serves one organization (one database, one active profile). Switching
organizations means redeploying with different environment variables and a
different database — not switching organizations at runtime within the same
process. See `ORGANIZATION_PLAN.md` for the full assessment and the
reasoning behind these choices, including why there is no `Organization`
database table.

### Creating a new organization deployment

1. **Backend profile** — create `backend/app/organizations/<id>/` with:
   - `config.py` exporting `ORGANIZATION = OrganizationConfig(id="<id>", name=..., short_name=..., product_name=..., features={...})`.
   - `seed_data.py` exporting `TEAM_DEFS`, `TAG_NAMES`, `USER_DEFS`, and a
     `seed(db: Session) -> None` function that builds that org's demo
     project/teams/tags/users/activities. Use
     `app/organizations/default/seed_data.py` as the minimal template, or
     `app/organizations/vortex/seed_data.py` for a fuller example.
2. **Frontend profile** — create `frontend/src/branding/profiles/<id>.ts`
   exporting a `branding: BrandingConfig` (product name, favicon path,
   `features`), and register it in the `PROFILES` map in
   `frontend/src/branding/index.ts`.
3. **Deploy** with `APP_ORGANIZATION=<id>` and `VITE_ORGANIZATION=<id>` set,
   pointing at a fresh database. Run migrations, then
   `python -m app.db.seed` once to seed that organization's demo data (skips
   automatically if the database already has data).
4. If the organization needs functionality no other deployment should get,
   add it under `backend/app/extensions/<id>/` or
   `frontend/src/extensions/<id>/`, gated by a flag in that org's `features`
   dict — never by checking the organization id directly in core code.

## Local development

### Backend

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env             # optional — defaults work for local dev
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m app.db.seed        # idempotent demo data, skips if already seeded
.venv\Scripts\python -m uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000/api/v1`, interactive docs at
`http://127.0.0.1:8000/docs`.

Run tests: `.venv\Scripts\python -m pytest`

The seed script prints the shared development-only password for every
seeded account (default `DevPassword123!`, overridable via
`APP_DEV_SEED_PASSWORD`). See **Authentication** below for the seeded
Admin/Lead/Member accounts to log in as.

### Frontend

```
cd frontend
npm install
npm run dev
```

App available at `http://localhost:5173`. The Vite dev server proxies
`/api/*` requests to `http://127.0.0.1:8000`, so no CORS configuration or
`.env` file is needed for local development — just have the backend running.
`VITE_ORGANIZATION` (see `frontend/.env.example`) defaults to `"default"`
and selects which branding profile is used.

### Database migrations

New model changes: `alembic revision --autogenerate -m "description"` then
`alembic upgrade head`. Migrations use SQLAlchemy batch mode so they remain
compatible with SQLite's limited `ALTER TABLE` support and with a future
PostgreSQL target.

## Current status

v0.1 (all 14 planned phases) shipped first; role-based access control
(Admin/Lead/Member, real authentication, invitations) was added afterward
as its own 12-phase project. See `CHANGELOG.md` for phase-by-phase
progress on both.

## Authentication

Real login, replacing the earlier mocked "Acting as" switcher. Sessions
are server-side (HttpOnly cookie, Argon2-hashed passwords, CSRF via a
double-submit cookie) — see `RBAC_PLAN.md` for the full design and
`AUTHORIZATION.md` for the permission matrix. New accounts are created by
invitation only (Admin/Lead-issued, accepted at `/accept-invitation`);
there is no public sign-up.

Seeded accounts (password: `DevPassword123!`, or your
`APP_DEV_SEED_PASSWORD` override) depend on the active organization profile
— see `backend/app/organizations/<id>/seed_data.py`. With the default,
neutral profile (`APP_ORGANIZATION=default`, the out-of-the-box setting):

| Email | Role |
|---|---|
| `admin@example.org` | Admin |
| `alice@example.org` | Lead — Engineering |
| `bob@example.org` | Lead — Design |
| `carol@example.org` | Member — Operations |

With the `vortex` profile (`APP_ORGANIZATION=vortex`):

| Email | Role |
|---|---|
| `admin@example.local` | Admin |
| `embedded.lead@example.local` | Lead — Embedded |
| `mechanical.lead@example.local` | Lead — Mechanical |
| `embedded.member@example.local` | Member — Embedded |
| `mechanical.member@example.local` | Member — Mechanical |

The original five demo users (`markus@example.org` and friends) also still
exist in the `vortex` profile, with real team memberships and the same
shared password.
