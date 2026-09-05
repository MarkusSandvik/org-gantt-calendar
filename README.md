# Org Gantt & Calendar

Local-first project planning and organization management system: Gantt chart,
calendar/week view, dashboard, and admin tools for a student organization's
technical and organizational activities.

See the full architecture proposal, database model, scheduling engine design,
and phased implementation plan discussed with the project owner before
implementation began (development phases are tracked in `CHANGELOG.md`).
Role-based access control (Admin/Lead/Member) was added after v0.1 shipped —
see `RBAC_PLAN.md` for that architecture and `AUTHORIZATION.md` for the live
permission matrix.

## Stack

- **Frontend:** React 19 + TypeScript, Vite, React Router, TanStack Query
- **Backend:** FastAPI, SQLAlchemy 2.0 (typed ORM), Alembic (migrations), Pydantic v2, Argon2 password hashing
- **Database:** SQLite locally (`backend/data/app.db`), PostgreSQL in later deployment

## Project layout

```
backend/
  app/
    core/       settings
    db/         engine/session, declarative base, seed script
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
    components/layout/   app shell, nav, shared placeholders
    pages/      one file per top-level view (Dashboard, Gantt, Calendar, ...)
```

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
`APP_DEV_SEED_PASSWORD` override):

| Email | Role |
|---|---|
| `admin@example.local` | Admin |
| `embedded.lead@example.local` | Lead — Embedded |
| `mechanical.lead@example.local` | Lead — Mechanical |
| `embedded.member@example.local` | Member — Embedded |
| `mechanical.member@example.local` | Member — Mechanical |

The original five demo users (`markus@example.org` and friends) still
exist too, now with real team memberships and the same shared password —
see `backend/app/db/seed.py`.
