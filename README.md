# Org Gantt & Calendar

Local-first project planning and organization management system: Gantt chart,
calendar/week view, dashboard, and admin tools for a student organization's
technical and organizational activities.

See the full architecture proposal, database model, scheduling engine design,
and phased implementation plan discussed with the project owner before
implementation began (development phases are tracked in `CHANGELOG.md`).

## Stack

- **Frontend:** React 19 + TypeScript, Vite, React Router, TanStack Query, Zustand
- **Backend:** FastAPI, SQLAlchemy 2.0 (typed ORM), Alembic (migrations), Pydantic v2
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
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m app.db.seed        # idempotent demo data, skips if already seeded
.venv\Scripts\python -m uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000/api/v1`, interactive docs at
`http://127.0.0.1:8000/docs`.

Run tests: `.venv\Scripts\python -m pytest`

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

v0.1 in progress — Phase 7 (calendar) is complete. See
`CHANGELOG.md` for phase-by-phase progress.

## Mocked authentication

There is no real login yet. The frontend's "Acting as" switcher (top-right)
lets you pick which seeded user is making requests; it's sent as an
`X-User-Id` header and used for `created_by` attribution. Direct API calls
without that header fall back to the first user in the database. This is
designed to be swapped for real auth later without changing call sites —
see `app/core/deps.py`.
