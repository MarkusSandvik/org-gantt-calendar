# Deployment — Setup and Integration Plan

This repository is public, and there's no real server yet to hold the
secrets (SMTP credentials, a production database URL, the real domain)
that some of this work needs — those parts (email integration, the actual
hosting choice, HTTPS/domain/CORS for a real domain) are deliberately
still just plans below, not yet built. A few secret-free, safe-to-build-
now pieces have been done ahead of the real server existing — each
section below says "— done" or "wired up, not yet run for real" when that
applies, and stays a plain plan otherwise.

## Bootstrapping a real production database — done

Resolved: `backend/app/db/bootstrap_admin.py` (`python -m
app.db.bootstrap_admin --email you@example.org --name "Your Name"`)
creates exactly one real Admin user and nothing else — no teams, tags,
activities, or demo users. It refuses to run if the `users` table already
has any row, so it can never be used as a second, conflicting seeding path
alongside `app/db/seed.py`. Pass `--password` explicitly, or omit it to
get a random one printed once to the terminal (not logged or stored
anywhere else). Once that Admin exists, every other structure (Teams,
Tags, the first real Project, more Users via invitation) is already fully
buildable through the Admin UI itself.

This was the one genuine blocker found while writing this plan, not just a
nice-to-have: the documented process for standing up a new deployment
(README's "Creating a new organization deployment") says to run
`python -m app.db.seed` after migrating, but that seeds **fake demo
data** — for the `vortex` profile specifically, made-up teams, made-up
activities, and demo user accounts that all share one publicly-known dev
password (`APP_DEV_SEED_PASSWORD`). `app/db/seed.py`'s only "already set
up" check is "does any `Project` row exist," so there was no path for
"give the real production database one real Admin account and nothing
else" before this script existed.

## Database: SQLite → PostgreSQL

The README already commits to this ("SQLite locally, PostgreSQL in later
deployment") — nothing here contradicts that, but it hasn't been exercised
against a real Postgres instance yet.

**Already fine, no change expected:**
- Alembic's batch mode (`render_as_batch=True`, unconditional in
  `alembic/env.py`) is a documented no-op on dialects that support a
  normal `ALTER TABLE`, including Postgres — it only actually rewrites the
  table on SQLite. Every existing migration should apply unchanged.
- `app/db/session.py` already conditions the SQLite-only
  `check_same_thread` connect arg on the database URL, so swapping
  `APP_DATABASE_URL` to a Postgres DSN needs no code change there.

**Wired up, not yet run for real:** `backend/tests/conftest.py`'s
`db_session` fixture now reads `TEST_DATABASE_URL` (falling back to the
original in-memory SQLite when unset), `psycopg2-binary` was added to
`requirements.txt`, and `.github/workflows/ci.yml` runs the full Alembic
migration chain plus the entire pytest suite against a real `postgres:16`
service container on every push, alongside the existing SQLite run. This
dev machine has no Docker and no local Postgres install, so this couldn't
be exercised against a real Postgres instance here — the SQLite side was
re-run locally (251 passed) to confirm the fixture change itself didn't
regress anything, but the Postgres leg has not actually executed yet. It
will run for real the first time this is pushed and CI executes; treat
the "no code change expected" claim above as still unconfirmed until that
first CI run is green.

## HTTPS, domain, and CORS

- `Settings.cookie_secure` already correctly flips on for any
  non-`local` environment (`app/core/config.py`) — no change needed there.
- `cors_origins` is hardcoded to `http://localhost:5173` today and needs
  the real domain once one exists.
- Needs a TLS certificate for that domain — a reverse proxy that handles
  Let's Encrypt automatically (e.g. Caddy) is the lowest-effort route for
  a small deployment; nginx + certbot is the more manual alternative.

## Frontend: serving the production build

Today the frontend is only ever run via Vite's dev server. Production
needs the actual `npm run build` output (`frontend/dist/`) served as
static files. Decide whether that's:
- the same host/process as the backend (the reverse proxy above serves
  `dist/` directly and proxies `/api/*` to the backend), or
- a separate static host (Netlify/Vercel/S3+CDN) pointed at the backend's
  own public URL.

The former is simpler for a single small deployment and avoids a second
thing to configure and pay for.

## Hosting choice

Not yet decided, and worth deciding explicitly rather than defaulting:
- **A VPS you manage** (systemd service running the backend, your own
  Postgres, your own reverse proxy/TLS) — full control, more to maintain.
- **A PaaS** (Railway, Render, Fly.io, etc.) — usually bundles a managed
  Postgres, TLS, and deploy-on-push, trading some control for much less
  ongoing ops work. Likely the better fit for a student org without
  dedicated infra time, but it's a real tradeoff to weigh, not an
  automatic choice.

## Continuous integration — done

`.github/workflows/ci.yml` runs on every push and pull request: a
`backend-test` job (matrix of SQLite and a real `postgres:16` service
container, see above) running the full pytest suite, and a
`frontend-build` job running `npm ci && npm run build` (which itself runs
`tsc -b` for type-checking before `vite build`). This doesn't replace
deciding a real hosting/deploy target below — it only catches breakage on
every push from here on.

## Backend container image — done

`backend/Dockerfile` builds a `python:3.12-slim` image running the FastAPI
app under `uvicorn` on port 8000 as a non-root user (`backend/.dockerignore`
keeps the local venv, `.env`, and the dev SQLite file out of the image).
It deliberately does **not** run `alembic upgrade head` in the container's
`CMD` — that stays a separate deploy step (see below) so it runs exactly
once per deploy, not once per replica on every container start. Not yet
built or run anywhere (no Docker on this dev machine) — the Dockerfile
itself has only been reviewed for correctness against the existing
`requirements.txt`/`app/` layout, not executed. There is no frontend
Dockerfile yet — that depends on the still-open "same host as backend vs.
separate static host" decision below.

## Migrations as part of deploy

`alembic upgrade head` needs to become an actual step in however deploys
happen (a PaaS's pre-deploy/release-phase hook, or a line in a deploy
script), not a command someone has to remember to run by hand.

## Backups

Once real season data lives in Postgres, it stops being something that
can just be regenerated from a seed script. Needs at minimum scheduled
automated backups (most managed-Postgres offerings on PaaS platforms
include this; a self-managed VPS needs `pg_dump` on a cron job and offsite
storage for the result).

## Known limitation to carry forward, not necessarily fix now

The login rate limiter (`app/services/auth.py`) is an in-memory
sliding-window counter. That's fine for a single process, but it would
silently stop enforcing correctly the moment the backend ever runs as
multiple worker processes (each worker keeps its own independent count).
Worth knowing about before scaling to multiple workers, not urgent before
that.

## Already fine — no change needed

Sessions are stored in the `auth_sessions` table, not in memory
(`RBAC_PLAN.md`) — they already survive restarts and would already work
correctly across multiple worker processes, unlike the rate limiter above.
No action item here; noted so it isn't re-investigated later.

## Email integration

Two flows generate a secure, single-use token today and stop short of
emailing it anywhere:

- **Invitations** (`app/services/invitations.py::create_invitation`) —
  generates the token and, only when `APP_ENVIRONMENT=local`, returns an
  `invite_url` field in the API response so the Admin UI can show a
  copy-paste link (`UsersAdmin.tsx`'s post-invite banner). Outside local
  dev, `invite_url` is `None` — the admin currently has no way to get the
  link at all except querying the database directly.
- **Password reset** (`app/services/auth.py::request_password_reset`) —
  generates the token and returns it to the router, which only prints the
  link to the server's own stdout, and only when `APP_ENVIRONMENT=local`
  (`app/routers/auth.py`). The HTTP response is always a bare 204 either
  way, by design, so the API can't be used to enumerate which emails have
  accounts.

There is no SMTP client, no third-party email provider integration, no
email templates, and no email-related settings anywhere in
`app/core/config.py` today.

### Prerequisite: a Google Workspace sending identity

Either a dedicated `no-reply@vortexntnu.no` account, or (recommended, no
extra license) an alias on an existing account — with 2-Step Verification
enabled and an **App Password** generated for it. See the chat history
for the fuller walkthrough of that decision.

### Backend changes required

1. **New settings** in `app/core/config.py` (same `APP_`-prefixed
   pattern as everything else there):
   - `smtp_host` (e.g. `smtp.gmail.com`)
   - `smtp_port` (`587`, STARTTLS)
   - `smtp_username` (the Workspace account authenticating, not
     necessarily the same as the From address if using an alias)
   - `smtp_password` (the App Password — a real secret, `.env`-only,
     never committed, matching how the repo already treats
     `backend/.env`)
   - `smtp_from_address` (`no-reply@vortexntnu.no`)
   - `smtp_from_name` (e.g. `"Vortex NTNU"` — could read from the active
     organization profile's `product_name` instead of a separate setting)

2. **New `app/services/email.py`** — a small wrapper around Python's
   stdlib `smtplib` (no new dependency needed for plain SMTP+STARTTLS).
   One function, e.g. `send_email(to, subject, body)`, used by both flows
   below. Keeping it to stdlib avoids picking a provider SDK before
   there's a reason to.

3. **Two plain-text templates** (start with plain text, not HTML — no
   design work, renders everywhere, easy to keep in sync):
   - Invitation email: who invited them, which org/team, the accept link,
     expiry.
   - Password reset email: the reset link, expiry, a line noting the
     request can be ignored if they didn't ask for it.

4. **Wire into `create_invitation`**: after the token is generated, call
   `email.send_email(...)` with the invite link. Decide then whether the
   local-dev `invite_url` response field stays as a same-time fallback
   (harmless, since it's already gated to `environment == "local"`) or is
   removed once real sending exists — recommend keeping it, since local
   dev has no mailbox to check.

5. **Wire into `request_password_reset`**: replace the
   `print(...)`-to-stdout dev stand-in with a real `email.send_email(...)`
   call outside local dev; keep the console-print for local dev unchanged.

6. **Decide failure handling**: recommend a send failure never fails the
   invitation-creation request itself — the invitation row is still
   created and valid, so an admin can still act on it (e.g. share the
   link manually) even if the mail server was briefly unreachable. Log
   the failure server-side; consider surfacing a "created, but the email
   may not have sent" toast in the Admin UI as a later refinement, not a
   blocker for the first version.

7. **Tests**: stub/monkeypatch `email.send_email` in the test suite so
   pytest never actually sends mail — assert it was *called* with the
   right recipient and that the token/link it was called with matches,
   rather than testing real delivery.

### Frontend changes required

Minimal. `UsersAdmin.tsx`'s post-invite banner already only renders when
`invite_url` is present, which will naturally stop happening once
`environment` isn't `"local"` — no change forced by that alone. Worth
adding once real sending exists: a toast confirming "Invitation emailed to
{email}" when `invite_url` is absent, so an admin gets *some* confirmation
something happened, rather than the banner simply not appearing.

### Configuration to set on the real server (never in the repo)

```
APP_SMTP_HOST=smtp.gmail.com
APP_SMTP_PORT=587
APP_SMTP_USERNAME=<the Workspace account used to authenticate>
APP_SMTP_PASSWORD=<the App Password>
APP_SMTP_FROM_ADDRESS=no-reply@vortexntnu.no
APP_SMTP_FROM_NAME=Vortex NTNU
```

(Alongside the deployment-wide settings from earlier sections:
`APP_DATABASE_URL`, `APP_CORS_ORIGINS`, `APP_ENVIRONMENT=production`.)

## Open decisions to make when this is picked back up

- Hosting choice: managed PaaS vs. self-managed VPS (above).
- Plain text vs. HTML email templates — recommend starting plain text.
- Synchronous email send inside the request vs. a background task —
  recommend synchronous to start; SMTP send is sub-second and this app has
  no task queue infrastructure today. Revisit only if it becomes a
  measured problem, not speculatively.
- Whether other events ever warrant an email (e.g. "your invitation was
  revoked") — not currently planned; out of scope unless asked for.

## Explicitly not in scope here

- Domain verification (SPF/DKIM) for a third-party transactional email
  API — not needed for the Google Workspace SMTP route this plan assumes.
- Bulk/marketing email, digest emails, or a notification-preferences UI —
  email integration here covers only the two existing transactional flows
  above.
- Monitoring/error-tracking (e.g. Sentry) and multi-worker/horizontal
  scaling — reasonable later additions, not needed for a first real
  deployment of this size. (Basic CI is no longer out of scope — see
  "Continuous integration" above.)
