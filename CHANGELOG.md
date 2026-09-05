# Changelog

## Organization abstraction (2026-09-05)

A third initiative, built after RBAC shipped: turning the single-org app
into a reusable platform any organization can deploy from the same
codebase, without forking or duplicating scheduling/authorization logic.
See `ORGANIZATION_PLAN.md` for the full assessment (existing-architecture
findings, the decisions below with their trade-offs, and the 11-phase
plan this summarizes).

**Key decisions:** no new `Organization` database table — `Project` already
scopes teams/tags/activities, and every table that would need
`organization_id` has none today, so it would be schema weight with no
behavioral payoff in a single-org-per-deployment model. Organization
identity is a deployment-time environment variable
(`APP_ORGANIZATION`/`VITE_ORGANIZATION`, both defaulting to `"default"`),
not runtime state. One repository, one `master` branch — org profiles live
side by side in the same codebase; there is no per-org fork or package.

**Config abstraction (Phase 1):** `backend/app/core/organization.py`
(`OrganizationConfig` + `get_active_organization()`, raising a clear error
on an unrecognized `APP_ORGANIZATION`) and the matching
`frontend/src/branding/` loader reading `VITE_ORGANIZATION`. Both default
to `"default"` so a fresh clone runs with zero configuration.

**Seed data extraction (Phase 2):** the real Vortex NTNU demo data (teams,
tags, users, activities, dependencies, milestones, calendar events) moved
from `backend/app/db/seed.py` into `app/organizations/vortex/seed_data.py`
unchanged; a new neutral `app/organizations/default/seed_data.py` was
written alongside it. `db/seed.py` is now a thin generic engine that
imports whichever profile is active and calls its `seed(db)`.

**Frontend branding (Phase 3) & remaining literals (Phase 4):** the two
hardcoded "Org Planner" strings (`AppShell.tsx`, `Login.tsx`) now read
`branding.productName`; `main.tsx` sets `document.title` and the favicon
href from the active profile at boot. The CSV import template's example
row no longer references a Vortex team name.

**Default/neutral profile (Phase 6):** a complete "Example Organization"
profile (Sample Project, Engineering/Design/Operations teams, four demo
users) ships in the repo so it boots and demonstrates Gantt/calendar/
scheduling standalone, with zero Vortex assets referenced — verified by
test and by a full `npm run build`.

**Extension boundary (Phase 7):** empty `backend/app/extensions/` and
`frontend/src/extensions/` directories, each with a README documenting the
convention: an extension is gated by a flag in the active profile's
`features` dict, and core never imports a specific extension by name.

**Theme retrofit (Phase 8):** `frontend/src/index.css`'s existing
`--color-*` token names got `@media (prefers-color-scheme: dark)` and
`[data-theme]` override blocks, plus ~17 new tokens (badge/status colors,
subtle borders/text, selection backgrounds) extracted from previously
hardcoded hex values so dark mode could reach them — saturated fills
(event chips, Gantt bars, priority dots) were deliberately left as literals
since they read fine on either background. A light/dark/system toggle in
the nav persists to `localStorage`. Verified live in the browser in all
three modes.

**Tests (Phase 9):** `backend/tests/test_organization.py` — profile
resolution (known org, default fallback, unknown-org error), both
profiles' `seed_data.seed()` running successfully against a fresh
database, the default profile referencing zero Vortex-specific data, and
a static-source assertion that `app/core/permissions.py` never hardcodes a
team or tag name from either profile.

No functional or behavioral change to Admin/Lead/Member permissions,
Gantt, scheduling, calendar, dashboard, baselines, or audit history — the
full backend test suite (201 pre-existing + new) stayed green throughout,
and the `vortex` profile reproduces the exact pre-refactor demo data.

## Role-based access control & authentication (2026-09-05)

A second, independently-approved initiative built after v0.1 shipped:
real authentication and an Admin/Lead/Member authorization model,
replacing the mocked `X-User-Id` header that every phase above was built
on. Planned and executed as its own 12-phase sequence — see
`RBAC_PLAN.md` for the full architecture writeup (assessment, schema,
authentication approach, and the risk/scope decisions below) and
`AUTHORIZATION.md` for the live permission matrix. Summarized here by
phase, in the same level of detail as the phases above.

**Schema (Phase 2):** `User` gained `password_hash`, `global_role`
(`USER`/`ADMIN`, replacing the unused `viewer`/`editor`/`admin` enum),
`status` (`PENDING`/`ACTIVE`/`INACTIVE`/`ARCHIVED`, replacing a plain
`active: bool`), and `last_login_at`. `TeamMembership` (present since
Phase 1 of the base app but never populated) gained `team_role`
(`MEMBER`/`LEAD`) and a unique `(team_id, user_id)` constraint. Three new
tables: `invitations`, `auth_sessions`, `password_reset_tokens`. One
Alembic migration, staged in three steps so SQLite's table-recreate-based
`ALTER TABLE` could backfill `global_role`/`status` from the old
`role`/`active` columns before dropping them, rather than losing data.

**Authentication (Phase 3):** HttpOnly, `SameSite=Lax` session cookies
backed by `auth_sessions` (only a SHA-256 hash of the token is ever
stored) — chosen over JWTs so logout and deactivate-while-logged-in are
a single row update, not a denylist. Argon2id password hashing. A
double-submit CSRF cookie/header pair, enforced by middleware only on
requests that already carry a session cookie (login/password-reset are
explicitly exempt — they establish or bypass a session, they don't use
one). An in-memory sliding-window login rate limiter. Generic
"Invalid email or password" for both unknown-email and wrong-password.

**Centralized authorization (Phase 4):** `app/core/permissions.py` — one
named `can_*` resolver per resource/action, each taking the real ORM row
(never a role string from the request), with `is_admin()` short-circuiting
every check. Full matrix in `AUTHORIZATION.md`.

**Protecting existing endpoints (Phase 5):** every mutating router gained
a `permissions.require(...)` call — including several that had **no**
identity resolution at all before this (activity delete, calendar-events
CRUD, dependency create/delete, milestone create/delete). Cross-team
scheduling impact is blocked outright: a Lead's `/scheduling/apply` or
`/undo` that would touch another team's activity/milestone or an
org-wide milestone returns 409 with the full impact list instead of
silently applying the in-team part (Section 7 of `RBAC_PLAN.md`). Import
now checks per-row team permission, not just parse validity.

**Invitations (Phase 6):** `POST /invitations` derives the caller's
allowed scope server-side — a Lead's request is checked against their
own team and forced to `MEMBER`, never trusting the payload's
`team_id`/`target_team_role` even if it claims otherwise. Tokens are
`secrets.token_urlsafe(32)`, only their SHA-256 hash persisted,
single-use, time-limited. `POST /invitations/accept` creates the account
and logs the user straight in.

**User administration (Phase 7):** `GET /users/admin` (Admin: everyone;
Lead: their own team's Members only), deactivate/reactivate,
`PUT/DELETE .../team-memberships` (promote/demote/move — promoting to
Lead of a new team auto-demotes any previous Lead team, since a user
leads at most one), and `PATCH .../global-role` — all Admin-only except
deactivate/reactivate, which a Lead can do for their own team's Members.

**Frontend login (Phase 8):** `/login`, `/accept-invitation`,
`/reset-password` — all public, outside the new `RequireAuth` route
guard wrapping the rest of the app. The old "Acting as" impersonation
switcher is gone entirely, replaced by real login/logout and a
`useCurrentUser()` hook backed by TanStack Query. `api/client.ts` no
longer sends `X-User-Id`; it sends cookies (`credentials: "include"`)
and echoes the CSRF cookie back as a header on mutating requests. Admin
> Users is a new page (invite modal, pending-invitations list with
revoke, per-user deactivate/reactivate, and — Admin only — inline
team-membership and global-role editing).

**Permission-aware UI (Phase 9):** a `usePermissions()` hook mirrors the
backend's resolvers. The Admin "Users" tab is hidden for plain Members;
"New Activity"/"New Milestone" buttons only render for someone who can
create somewhere; `ActivityFormModal`/`MilestoneFormModal` disable
fields down to nothing (view-only, with an explanatory hint) or down to
just status/progress (assigned Members) depending on who's looking;
Gantt bars and milestone diamonds only open the reschedule modal for
someone with edit rights on that item; the comment box hides when the
viewer isn't allowed to comment. Every one of these is a convenience —
the backend re-checks regardless.

**Audit events (Phase 10):** invite/revoke/activate/deactivate/role-change
/membership-add/membership-remove/password-reset all write `AuditLog`
rows via the existing `write_field_changes()` helper — no schema change
needed, since it was already fully generic. "Failed privileged action"
(the one event Section 17 marks optional) is deliberately not
implemented — see `RBAC_PLAN.md`'s note on why a global exception
handler for it would have broken the test suite's DB-session isolation.

**Tests (Phase 11):** `test_auth.py`, `test_permissions.py` (unit tests
against the resolvers directly), `test_authorization_endpoints.py` (the
full Member/Lead/Admin/security matrix from Section 23, exercised
through real HTTP requests), `test_invitations.py`, `test_user_admin.py`,
`test_audit_events.py`, plus `test_rbac_schema.py` from Phase 2 — 98 new
tests, taking the suite from 102 to 200. Two Section 25 cases (an
activity with no owner team or user) are covered explicitly: viewable by
everyone, editable by nobody but Admin, never a 500.

**Verified:** 200/200 backend tests pass, including every scenario in
`AUTHORIZATION.md`'s matrix. Checked end-to-end in a browser: logged in
as the seeded Admin,
invited a Member via the dev-mode invite-link banner, accepted that
invitation (auto-logged-in, correct role shown), logged in as a Member
and confirmed an unassigned activity renders fully read-only with the
correct explanatory hint and no Save/Delete controls, and confirmed
`/admin/users` and the "New Activity" button are correctly absent for
that Member.

**Not yet implemented / deliberately deferred (see `RBAC_PLAN.md`):** a
persisted pending-approval object for cross-team scheduling changes
(the hard block is fully implemented; the softer "queue it for Admin to
approve" workflow is optional follow-on scope); Tag management (no
mutation endpoints exist for tags at all, RBAC or otherwise); Team
management UI (still admin-read-only, as before this initiative).

## Phase 14 — My Tasks + polish (2026-09-05)

The last phase of the original plan: a personal view of what the acting
user owns or contributes to, plus a couple of app-wide rough edges
closed out along the way.

**Backend**
- `GET /milestones` and `GET /calendar-events` both gained an
  `owner_user_id` filter, mirroring the one activities already had since
  Phase 4 — needed so My Tasks can ask each endpoint for "mine" directly
  instead of fetching everything and filtering client-side. 2 new tests
  (102/102 total).

**Frontend**
- `/my-tasks` (previously a placeholder) is now a real page, scoped to
  whichever user is selected in "Acting as": **My Activities** (owned
  activities merged with contributed-to ones, deduplicated, sorted by
  end date — clicking a row jumps to a pre-filtered Admin > Activities
  view, the same navigation pattern the Dashboard's "Attention Required"
  list already used), **My Milestones** (owned, excluding
  `completed`/`missed`, sorted by date), and **My Upcoming Events**
  (owned, from today forward). Prompts the user to pick someone from
  "Acting as" first if no user is selected yet, rather than silently
  showing nothing.
- Added a catch-all `*` route rendering a small "Page not found" page
  (with a link back to the Dashboard) inside the app shell — previously
  an unknown URL rendered a blank content area with no explanation.

**Verified:** 102/102 backend tests pass, frontend type-checks clean.
Checked in a browser as two different users: Emil showed his one owned
activity plus one he only contributes to, correctly merged into a single
sorted list; switching to Ola showed her four owned activities (delayed
ones correctly badged), her one outstanding milestone, and an empty
upcoming-events state. Clicking an activity row correctly navigated to
`/admin/activities?q=<title>`. Navigating to a nonexistent URL rendered
the new not-found page with the sidebar still intact, and its link
correctly returned to the Dashboard.

**Not yet implemented / deliberately deferred:** full Teams/Tags/Users
admin CRUD (still read-only, supporting other forms' selects only, as
established since Phase 2) and a Settings page — neither was ever a
numbered phase in the original plan, and nothing in this phase depended
on them. This closes the 14-phase v0.1 plan; further work is
follow-on polish or new scope, not a gap in the original plan.

## Phase 13 — Export (2026-09-04)

The counterpart to Phase 12: download the current plan as CSV or XLSX
instead of only bulk-loading into it.

**Backend**
- `app/services/export_data.py` builds export rows straight from live
  Activity/Milestone data, resolving `owner_team`/`owner_user`/
  `contributors`/tags to names (never raw ids) via the same lookups
  Phase 12's import already relies on.
- `GET /export/activities.csv` writes activities using **exactly** the
  same header row as `/import/activities/preview` expects
  (`app.services.import_activities.EXPECTED_COLUMNS`, imported directly
  rather than duplicated) — the file this endpoint produces can be
  edited and fed straight back into import with zero errors. Multi-value
  fields (contributors, tags) are comma-joined; the CSV writer's own
  quoting handles the resulting embedded commas correctly.
- `GET /export/plan.xlsx` produces a two-sheet workbook — "Activities"
  (same layout as the CSV) and "Milestones" (title, description, date,
  status, team, owner, tags) — since a milestone has no natural home in
  the activity-shaped CSV format.
- 5 new tests (100/100 total): CSV header correctness, resolved-name
  content, empty-project export (header only, not an error), a
  round-trip test that exports then re-imports the same file through
  `/import/activities/preview` and asserts zero errors, and an XLSX test
  that reads both sheets back with `openpyxl` and checks their headers
  and data.

**Frontend**
- Admin > Import / Export gained an "Export" section above the existing
  import UI: two plain download links (`Export activities (CSV)`,
  `Export full plan (XLSX)`) — no client-side state needed, since these
  are simple `GET` downloads rather than a preview/apply flow.

**Verified:** 100/100 backend tests pass, frontend type-checks clean.
Checked end-to-end against the live seed data: exported the CSV via a
direct request, confirmed it round-trips through `/import/activities/
preview` with `valid_count: 9, error_count: 0` on all nine seeded
activities (including multi-value contributor/tag fields quoted
correctly), and exported the XLSX and confirmed both sheets and their
headers via the response's content-type/disposition headers and byte
size. Checked in a browser that both export links and the existing
import controls render correctly side by side on the same page.

**Not yet implemented:** PDF export and print-friendly views (not
requested by the master spec for v0.1); export currently covers the
same entity scope as import (activities primarily, milestones added to
the XLSX only) — extending either to dependencies or calendar events is
additive, following the same pattern.

## Phase 12 — Import CSV/Excel (2026-09-04)

Bulk-create activities from a spreadsheet, following the same
never-write-silently principle the scheduling engine established in
Phase 6: a mandatory preview step shows exactly what will happen before
anything is committed.

**Scope decision:** the master spec's "Import CSV/Excel" phase doesn't
pin down which entity types are importable. Activities are the entity
organizations actually need to bulk-load (a season's worth of planned
tasks from a spreadsheet used before this tool existed); milestones,
dependencies, and calendar events remain single-item admin flows for now
— nothing about the import pipeline below is activity-specific at the
architecture level, so extending it to another entity type later is
additive, not a rework.

**Backend**
- `app/services/import_activities.py::parse_upload` reads either a
  `.csv` or `.xlsx` file into normalized `{header: cell}` rows (headers
  are lowercased and space/dash-normalized, so "Owner Team" and
  "owner_team" are equivalent); XLSX support uses `openpyxl` (new
  dependency), CSV uses the standard library. Fully blank lines are
  skipped rather than treated as invalid rows.
- Row validation resolves `owner_team`/`owner_user`/`contributors`/`tags`
  by name (case-insensitive; users may also be matched by email) against
  existing Teams/Users/Tags — matching the rest of the app's rule that
  these references must already exist, rather than silently
  auto-creating them from typos in a spreadsheet. Dates must be
  `YYYY-MM-DD`; `status`/`priority` accept the same enum values used
  everywhere else in the API, defaulting to `not_started`/`normal` when
  left blank.
- `POST /import/activities/preview` parses and validates without writing
  anything, returning every row (valid or not) with its specific error
  list. `POST /import/activities/apply` **re-parses and re-validates the
  uploaded file itself** rather than trusting a client-submitted preview
  result — the same "never trust a client-submitted diff" rule the
  scheduling engine's `/apply` endpoint follows — then creates one
  Activity per valid row via the existing `activities.create_activity`
  service (so import gets the same date/reference validation as the
  admin form, for free) and reports created vs. skipped counts.
- `GET /import/activities/template` serves a downloadable CSV with the
  exact expected header row and one example line.
- 13 new tests (95/95 total): valid-row pass-through, name-based
  team/user/tag resolution, missing-required-field errors, end-before-
  start rejection, unknown-reference errors (team/user/contributor/tag),
  invalid status/priority values, preview writing nothing, apply
  creating only the valid rows and correctly linking resolved
  references, apply re-validating rather than trusting prior state,
  unsupported file extensions, and a real `.xlsx` file built with
  `openpyxl` end-to-end.

**Frontend**
- Admin > Import / Export (replacing the "Arrives in Phase 12"
  placeholder): pick a `.csv`/`.xlsx` file (or grab the template first),
  see every row in a table — errors shown inline per row, invalid rows
  highlighted — then a single "Import N rows" button that only imports
  the rows that passed validation. After applying, the same table
  updates to show what was actually created.
- `api/client.ts` gained `postForm`, a small variant of the JSON request
  helper that sends `FormData` without forcing a JSON `Content-Type`
  header (the browser sets the correct multipart boundary itself) while
  still attaching the `X-User-Id` header like every other mutating call.

**Verified:** 95/95 backend tests pass, frontend type-checks clean.
Checked end-to-end in a browser with a 4-row CSV (2 valid rows
referencing real seeded teams/users by name, 1 row missing its dates, 1
row referencing a non-existent team) — the preview correctly showed 2
"Ready" rows and 2 rows with their specific error messages, and
"Import 2 rows" created exactly those two activities with their owner
team, owner user, contributors, and tags all correctly linked (confirmed
via a direct API query, not just the UI) — the two invalid rows were not
written. Also confirmed a real `.xlsx` upload parses correctly via the
backend test suite. Test data removed via the API afterward.

**Not yet implemented:** import for milestones/dependencies/calendar
events (see the scope decision above — the pipeline is structured to
extend to these later without a rework), and Excel export (Phase 13).

## Phase 11 — Baselines (2026-09-04)

Plan-vs-actual comparison: snapshot every activity's and milestone's
currently planned dates under a named baseline, then see how far the live
plan has drifted from it later — the read-only counterpart to Phase 6's
scheduling engine, which is what actually moves the dates baselines get
compared against.

**Model fix found and corrected before building on it:** `Baseline` had a
`created_by_id` foreign-key column since Phase 1 but no matching ORM
relationship, so `BaselineRead.model_validate(baseline)` failed with
`created_by Field required` the moment the read schema tried to resolve
it. Added `created_by: Mapped["User"] = relationship()` to the model — a
Python-level addition only, no migration needed since the column already
existed.

**Backend**
- `app/services/baselines.py::create_baseline` snapshots every Activity and
  Milestone in the project into `BaselineActivity`/`BaselineMilestone` rows
  under a new `Baseline` row. Baselines are never overwritten — creating a
  new one never touches an earlier one, so historical snapshots stay
  comparable against each other as well as against the live plan.
- `get_baseline_comparison` joins each snapshot row against the entity's
  current state, computing `delta_start_days`/`delta_end_days`; an entity
  deleted since the baseline was taken is skipped rather than erroring
  (`db.get()` returning `None`), and results are sorted by
  `abs(delta_end_days)` descending so the largest drift surfaces first.
- `GET/POST /baselines?project_id=`, `GET /baselines/{id}/comparison`.
- 8 new tests (82/82 total): snapshot accuracy, multiple baselines
  coexisting without overwriting, drift reflecting a later change,
  comparison omitting a since-deleted activity, milestone drift, sort
  order, list ordering, and unknown-baseline 404.

**Frontend**
- Admin > Baselines (replacing the "Arrives in Phase 11" placeholder): a
  "Set Baseline" button/modal (name pre-filled with today's date, optional
  note), a table of existing baselines, and — on selecting one — a
  comparison table (Item / Baseline / Current / Drift) with milestones
  shown as a single date and activities as a range. Drift is colored red
  for later (`baseline-drift--later`), green for earlier
  (`baseline-drift--earlier`), and muted for "On schedule".

**Verified:** 82/82 backend tests pass, frontend type-checks clean.
Checked end-to-end in a browser: created a baseline against the unmodified
seed data (all 13 items correctly "On schedule"), then rescheduled PCB
Design's end date by 7 days via the Gantt's `RescheduleModal` and let
Phase 6's propagation cascade through its dependency chain. Re-selecting
the same baseline correctly showed PCB Design +7d, PCB Assembly +5d,
System Integration +3d, and Pool Test +2d — each matching the lag-adjusted
cascade from Phase 6 — all in red, while every unrelated activity and
milestone still read "On schedule".

**Not yet implemented:** a baseline-vs-current overlay directly on the
Gantt chart itself (the spec's comparison view is satisfied by the Admin
table above); this remains a candidate for later polish, not a v0.1 gap.

## Phase 10 — Comments and activity log (2026-09-04)

Activities and milestones get a real chronological history — the master
spec's explicit alternative to "one comment field that gets overwritten" —
synthesized with the field-level audit trail the scheduling engine has
been writing since Phase 6, so both show up in one merged timeline instead
of two disconnected places.

**Model fix found and corrected before building on it:** `Comment.
status_change_from/to` were typed as `ActivityStatus` only, but Comments
also attach to milestones, which use a different, non-overlapping status
enum (`at_risk`, `missed`, etc. don't exist on `ActivityStatus`). Changed
both columns to plain strings via a proper Alembic migration (batch mode,
as established since Phase 1) rather than working around it — storing an
enum's `.value` works for either entity type and doesn't privilege one
over the other.

**Backend**
- `GET/POST /activities/{id}/comments` and the same for milestones —
  deliberately append-only, no PATCH/DELETE, matching the spec's "history
  must remain available" framing.
- `PATCH /activities/{id}` and `/milestones/{id}` now write an `AuditLog`
  row (sharing one `change_group_id`, same convention the scheduling
  engine uses) for every changed *scalar* field — title, dates,
  progress, priority, owner/team — accepting an optional `reason`.
  `status` is deliberately excluded from this generic diff: a status
  transition instead auto-creates a `Comment` with `status_change_from/to`
  populated, since the spec frames status changes as belonging in the
  chronological log, not the field-audit trail. Enum values are stored via
  explicit `.value` rather than `str()`, sidestepping a real Python-version-
  dependent formatting difference for `(str, Enum)` mixins.
- New `GET /audit-log?entity_type=&entity_id=` read endpoint (audit log
  entries existed since Phase 6 but were write-only until now).
- 18 new tests (74/74 total): comment ordering, empty-body rejection,
  auto status-change comments (with and without a reason), no-op updates
  writing nothing, status changes correctly absent from the audit log, and
  audit entries scoped correctly per entity.

**Frontend**
- `ActivityLogPanel`, shared by both `ActivityFormModal` and
  `MilestoneFormModal` (rendered only when editing an existing entity, not
  while creating one): fetches comments and audit-log entries for that
  entity and merges them into one chronological list — status-change
  comments and plain notes rendered distinctly from field-change entries,
  which resolve `owner_team_id`/`owner_user_id`/`team_id` values to names
  client-side (using the teams/users lists the parent form already has)
  rather than showing raw database ids. A plain textarea posts new notes.
- Both edit forms gained an optional "Reason for this change" input,
  applied to whichever of the audit trail / status-change comment ends up
  being written by that save.

**Verified:** 74/74 backend tests pass, frontend type-checks clean.
Checked end-to-end in a browser: added a manual note, then in one save
changed both priority (high → critical) and status (delayed → in
progress) with a shared reason — the resulting log correctly showed all
three entries in chronological order, with the field-change entry showing
"Reason: ..." and the status-change entry using the same text as its
comment body. Reset the local dev database afterward (comments have no
delete endpoint by design) rather than leaving test data in the seed
fixture.

## Phase 9 — Dashboard (2026-09-04)

The operational-overview landing page — the last piece of v0.1's "Data" /
"Project Management" surface that was still a placeholder.

**Backend**
- `GET /dashboard/summary?project_id=` — a single aggregated endpoint (per
  the architecture proposal's own reasoning: avoid N+1 dashboard calls),
  returning:
  - `week_counts`: active tasks (in-progress activities), milestones this
    week, delayed, blocked, social activities, meetings, and upcoming
    deadlines (the last three scoped to calendar events overlapping the
    current ISO week). The API always returns every count, including
    zeros — hiding "meaningless zero-value categories" is presentation
    logic and stays in the frontend, not baked into what the API reports.
  - `upcoming_milestones`: the next 5 milestones from today, excluding
    ones already `completed` or `missed`.
  - `attention_required`: every delayed activity (with a computed "N days
    delayed", falling back to "Delayed" if not yet past its end date) and
    every blocked activity — for blocked items, it walks the dependency
    graph for an incomplete predecessor and names it ("Blocked by X"),
    falling back to a plain "Blocked" when no dependency explains it
    (there's no separate free-text "reason" field on Activity, only the
    dependency graph and the status itself).
  - 6 new tests (62/62 total), including one confirming the dependency-
    derived blocker detail and one confirming the plain fallback.

**Frontend**
- `Dashboard` (previously just a connectivity check since Phase 1) is now
  the real operational overview: a metrics row that filters out zero
  counts before rendering, "Upcoming Milestones", "Attention Required"
  (clickable — takes you to the filtered Admin Activities view via the
  same URL-filter mechanism global search already uses), and "This Week's
  Schedule" (Monday–Friday, per the master spec's own example), which
  reuses the day-bucketing approach `CalendarWeekPage` already established
  rather than inventing a second way to group events by day.

**Verified:** 62/62 backend tests pass, frontend type-checks clean.
Checked in a browser against the seed data: the metrics row correctly
showed only 3 tiles (active tasks, delayed, blocked) with the four
zero-value categories (milestones/social/meetings/deadlines) hidden,
Attention Required showed Battery Enclosure's "6 days delayed" computed
correctly against today's date, and clicking it navigated to the filtered
Admin view. The empty "This Week's Schedule" was also correctly empty —
the seed calendar events are dated for the following week, so this is
accurate, not a bug.

## Phase 8 — Milestones (2026-09-04)

Milestones become fully manageable rather than read-only, and get a
dedicated primary-nav page.

**Backend**
- `GET /milestones` was already read-only (Phase 1/4). Added
  `POST/PATCH/DELETE /milestones`, tag support (milestones can now carry
  tags via `TagAssociation`, same polymorphic pattern as activities), and
  a dependency delete-guard mirroring the one activities have had since
  Phase 2 — a milestone that's part of a dependency can't be deleted until
  the dependency is removed. 7 new tests (56/56 total).

**Frontend**
- `/milestones` — previously a placeholder — is now a full list + create/
  edit page: table (title, date, team, owner, status, tags), filters
  (team, status, search), and `MilestoneFormModal`.
- The same guard `ActivityFormModal` got in Phase 6 now applies to
  milestones too: a milestone that appears in any `Dependency` has its
  date field disabled in the form, with a hint pointing at the Gantt's
  reschedule flow (clicking the milestone's diamond) — keeping date
  changes for anything in the dependency graph going through the one path
  that runs propagation and writes an audit trail, consistent with the
  activity behavior.

**Verified:** 56/56 backend tests pass, frontend type-checks clean.
Checked in a browser: all 4 seeded milestones list correctly, created and
then deleted a real milestone via the API to confirm the round-trip, and
temporarily linked a milestone into a dependency (via direct API calls,
cleaned up after) to confirm the date-field guard renders exactly as
designed before removing the test data. The Gantt (which already rendered
milestones since Phase 3) continues to work unchanged.

**Not yet implemented:** dashboard integration — deferred until the
Dashboard itself exists (Phase 9); today's Dashboard is still the Phase 1
connectivity-check placeholder, so there's nothing to integrate milestones
*into* yet. The Gantt half of "Gantt + dashboard integration" from the
original phase plan was already done in Phase 3.

## Phase 7 — Calendar (2026-09-04)

The primary short-term organizational planning view: a month grid and a
week-detail view, both reachable from each other and from the Gantt.

**Architecture note — deviation from the original proposal:** the initial
architecture doc recommended FullCalendar for the calendar grid. Building
it, I went custom instead: Phase 3 had already produced solid, correct ISO
week/date-math utilities (`getISOWeek`, `addDays`, etc.), a month grid on
top of them is not complex, and matching FullCalendar's theming to this
app's existing design system would have cost more than writing the grid
directly. Recurrence (the main thing FullCalendar would have bought)
remains explicitly out of scope for v0.1 per the master spec, so nothing
was actually given up. `CalendarEvent.recurrence_rule` still exists on the
model, unused, for whenever that lands.

**Refactor:** extracted `parseISODate`/`daysBetween`/`addDays`/`getISOWeek`
out of `components/gantt/dateScale.ts` into a shared `utils/date.ts` (re-
exported from `dateScale.ts` so no existing Gantt import had to change),
plus added `formatISODate` and `isoWeekToMonday`. Both the Gantt and the
new Calendar need the exact same ISO week math — keeping it in one place
means it can only be wrong in one place.

**Backend**
- Full `CalendarEvent` CRUD (`GET/POST/PATCH/DELETE /calendar-events`),
  the last of the five core entities (Activity, Milestone, Dependency,
  Tag, CalendarEvent) to get one — filters by project/team/event type, and
  by date range using the same overlap semantics as activities'
  `date_from`/`date_to` from Phase 4. 7 new tests (49/49 total).

**Frontend**
- `MonthGrid`: a Monday-start month grid with a clickable ISO week number
  per row (`buildMonthGrid` in `monthLayout.ts` pads in the leading/
  trailing days from adjacent months), today highlighted, and events shown
  as colored chips per day (one color per `CalendarEventType`). Clicking a
  day opens the create-event modal pre-filled with that date; clicking an
  event opens it for editing.
- `CalendarEventModal`: title/description/type/location/team/owner/related-
  activity, with an all-day toggle that swaps the start/end inputs between
  `date` and `datetime-local`.
- `CalendarWeekPage` at `/calendar/week/:isoYear/:isoWeek`: day-by-day
  event list plus a "Running project activities" panel — activities whose
  date range overlaps the week, with status/priority/progress — reusing
  the `date_from`/`date_to` activity filter from Phase 4 rather than
  needing anything new. Matches the master spec's own week-view example
  closely enough that it was useful as an informal acceptance check.
- Week numbers are now clickable in *both* places the spec asks for: the
  Gantt's timeline header (added an `onWeekClick` prop to
  `TimelineHeader`) and the Calendar's month grid — both navigate to the
  same week route.

**Renamed while building this:** `monthGrid.ts` (the layout util) collided
with `MonthGrid.tsx` (the component) on Windows' case-insensitive
filesystem — TypeScript reported it as a real error (TS1261/TS1149), not
a silent bug, so it was caught immediately. Renamed the util to
`monthLayout.ts`.

**Verified:** 49/49 backend tests pass, frontend type-checks clean.
Checked in a browser against the seed data: the month grid placed all 6
seeded events on their correct days and colors, clicking week 37 from
*both* the Calendar's gutter and the Gantt's header navigated to the same
week view showing the exact Monday–Friday schedule from the master spec's
own example plus the correct set of overlapping activities, and creating
then deleting a real event round-tripped correctly (confirmed via direct
API query, not just the UI).

**Not yet implemented:** recurring events (explicitly deferred per the
master spec), a day view, drag-to-reschedule for calendar events (Gantt
activities already have this via Phase 6's reschedule modal; events don't
participate in the dependency graph so there's nothing to propagate).

## Phase 6 — Scheduling engine (2026-09-04)

Dependency-aware date propagation with a mandatory preview step — the
master spec's core rule that dates must never change silently, now
actually enforced end-to-end rather than just designed for.

**Backend**
- `app/services/scheduling.py::compute_propagation` — the pure algorithm,
  framework-free (no DB, no FastAPI): forward-only, lag-aware,
  duration-preserving BFS relaxation over the dependency graph. A
  predecessor finishing later pushes each successor's start (and, keeping
  its duration fixed, its end) forward by exactly what's needed to satisfy
  the dependency's lag; a predecessor finishing *earlier* never pulls a
  successor forward — only a later date ever forces a change, which is why
  this always terminates on the DAG that Phase 5's cycle prevention
  guarantees. 7 unit tests written directly against this function, before
  the API layer existed, per the project's own testing principle for
  scheduling logic: chain propagation, lag respected (including a
  already-satisfied lag causing no push), pulling a predecessor earlier not
  cascading, a diamond dependency correctly converging on the *larger* of
  two competing pushes (not just the first edge relaxed), and milestones
  as zero-duration nodes in the graph on both ends of an edge.
- `POST /scheduling/preview` runs the algorithm read-only against live
  data and returns every affected item — writes nothing.
- `POST /scheduling/apply` recomputes the same result server-side (never
  trusts a client-submitted diff) and commits it, writing one `AuditLog`
  row per changed date field, all sharing a single generated
  `change_group_id`.
- `POST /scheduling/undo` reverts every row tagged with a given
  `change_group_id` by restoring each field's `old_value` — and is itself
  audited under a *new* change_group_id, so undoing is never a silent,
  untracked action either.
- 8 API-level tests: preview persists nothing, apply persists + writes the
  expected audit rows, apply on a node with no dependents still updates
  just that one node, undo reverts dates and is itself audited under a
  distinct group id, undo of an unknown group 404s, preview of an unknown
  entity 404s, end-before-start is rejected, and a milestone-initiated
  change propagates into a dependent activity.

**Frontend**
- Gantt bars and milestone markers are now clickable, opening
  `RescheduleModal` — editing the date(s) live-previews cascading impact
  (debounced, via `/scheduling/preview`) as a table of affected items
  before any commit, then an explicit "Apply changes" writes it via
  `/scheduling/apply`. A "Schedule updated. [Undo]" affordance appears
  immediately after applying.
- This is now the *only* way dates move for anything with dependency
  links — `ActivityFormModal`'s date fields are disabled (with an
  explanatory hint) for any activity that appears as either end of a
  `Dependency`, closing off a path that would otherwise silently bypass
  both propagation and audit logging. Activities with no dependency links
  keep the simple direct-edit behavior from Phase 2 unchanged.
- Milestones — which still have no dedicated admin CRUD — are reschedulable
  through this same modal, since it was already built to handle both
  entity types.

**Deliberately out of scope for v0.1** (per the original architecture
proposal): the `Project.auto_scheduling_enabled` flag exists on the model
but isn't wired to any behavior yet — every reschedule always shows a
preview before applying, regardless of that flag. The flag remains a
placeholder for a future refinement (e.g. auto-applying non-conflicting
pushes without confirmation), not a design gap — "never silently change
dates" is treated as an absolute rule for v0.1, not a toggle.

**Verified:** 42/42 backend tests pass (8 new since Phase 5, on top of the
7 pure-algorithm tests), frontend type-checks clean. Checked end-to-end in
a browser: pushing PCB Design's end date by 7 days produced a live preview
matching hand-calculated values for all three downstream links (PCB
Assembly +5d, System Integration +3d, Pool Test +2d — each reflecting that
link's lag and preserved duration), applying it updated the Gantt
immediately, and Undo restored every affected activity's dates to their
exact original values (confirmed via direct API query, not just the UI).
Also confirmed the Admin form correctly disables date fields only for
dependency-linked activities (PCB Design) while leaving unlinked ones
(Battery Enclosure) freely editable as before.

**Not yet implemented:** critical path analysis (still explicitly deferred
per the master spec), baselines (Phase 11).

## Phase 5 — Dependencies (2026-09-04)

Dependency modeling, cycle prevention, and arrow visualization in the
Gantt. Auto-scheduling / schedule propagation is explicitly out of scope
here — that's Phase 6, per the architecture proposal.

**Backend**
- `GET/POST/DELETE /dependencies`. Endpoints are polymorphic (an
  activity or a milestone can be either end), matching the `Dependency`
  model from Phase 1.
- Cycle prevention: on create, a BFS from the proposed successor over
  existing edges checks whether it can already reach the proposed
  predecessor — if so, the new edge would close a loop and is rejected
  (409) before it's ever written. Self-referential edges (422) and exact
  duplicate edges (409) are also rejected.
- `DependencyRead` resolves human-readable `predecessor_label` /
  `successor_label` (the activity/milestone title) so the frontend doesn't
  need a second round-trip to display a dependency list.
- 8 new pytest cases: create, self-loop rejection, duplicate rejection,
  cycle rejection (A→B, B→C, then C→A), unknown-endpoint 404,
  activity↔milestone cross-type dependency, list with labels, delete.

**Frontend**
- Admin > Dependencies: a real page (replacing the "Arrives in Phase 5"
  placeholder) — a form to add a dependency (predecessor/successor pickers
  spanning both activities and milestones, lag days) and a table of
  existing ones with remove buttons. Backend validation errors (cycle,
  duplicate, self-loop) surface directly in the form.
- Gantt: dependency arrows, drawn as an SVG overlay using a three-segment
  elbow connector with an arrowhead marker. `rowLayout.ts` computes each
  visible row's pixel position by walking the same milestones + team-group
  structure the Gantt renders (in the same order), so an arrow can connect
  any two rows — including across different team groups, which needed a
  reliable y-coordinate for every row regardless of which group it's in.
  Arrows respect the active filters: if either endpoint of a dependency
  isn't currently visible (filtered out), that arrow is silently skipped
  rather than pointing at nothing.
- Fixed while verifying this: `ApiError` was surfacing the raw JSON
  response body (`{"detail":"..."}`) as the error message shown to the
  user. `api/client.ts` now extracts FastAPI's `detail` field — a plain
  string for `HTTPException`, or a joined list of messages for a 422
  validation error — falling back to the raw text only if neither shape
  matches. This fixes error messages across every form, not just
  Dependencies.

**A layout constant now has to stay in two places:** `ROW_HEIGHT` and
`GROUP_HEADER_HEIGHT` in `rowLayout.ts` must match the actual rendered row/
group-header heights, which are now set via matching inline styles (not
just CSS) precisely so this can't silently drift. If a future change
resizes Gantt rows or group headers, both need to move together or arrows
will land on the wrong row.

**Verified:** 27/27 backend tests pass, frontend type-checks clean, checked
in a browser against the seed data's existing PCB Design → PCB Assembly →
System Integration → Pool Test chain — arrows render correctly at every
zoom level, including the one link that crosses from the Electrical group
down through Embedded, confirming cross-group position math. Also
confirmed in the browser that closing that chain into a cycle (Pool Test →
PCB Design) is correctly rejected with a clear error message.

**Not yet implemented:** schedule propagation/preview/apply/undo (Phase 6),
critical path analysis (explicitly deferred per the master spec until the
dependency model — now in place — supports it).

## Phase 4 — Filters + search (2026-09-04)

Every filter dimension the master spec lists for activities, applied
consistently everywhere activities are listed, plus a simple global search
across every entity type.

**Backend**
- `GET /activities` gains `tag_id`, `contributor_user_id`, `date_from`,
  `date_to` (in addition to the `team_id`/`owner_user_id`/`status`/
  `priority`/`q` from Phase 2). Date-range filtering uses overlap semantics
  (`end_date >= date_from AND start_date <= date_to`), not exact containment,
  so an activity spanning a filtered range is included even if it started
  earlier or finishes later.
- `GET /milestones` gains `team_id`, `date_from`, `date_to`, `q`.
- `GET /search?q=` — a simple global search (per the master spec's "first
  version may implement a simpler search") across activity titles, milestone
  titles, team names, tag names, and user names, capped at 8 results per
  type and requiring at least 2 characters.
- 6 new pytest cases (tag filter, contributor filter, date-range filter ×2,
  search-across-types, search minimum-length/no-match).

**Frontend**
- `useActivityFilters`: a `useSearchParams`-backed hook shared by every view
  that filters activities. Filters live in the URL rather than component
  state, so they're shareable/bookmarkable and — more importantly — so
  global search results can link straight into a pre-filtered view instead
  of needing a second piece of shared state.
- `FilterBar`: one shared component (search, team, owner, contributor, tag,
  status, priority, date range, plus "Delayed only"/"Blocked only" quick
  toggles) now used identically by the Gantt and by Admin > Activities,
  replacing the ad hoc filter bar Admin had before.
- Gantt: applying filters narrows which activities/milestones render and
  collapses team groups that end up empty, but does **not** rescale the
  visible date range — that's still driven by the full unfiltered project
  span, fetched separately, so narrowing a filter doesn't also disorient the
  user by zooming the whole chart to just the filtered data's span.
- `GlobalSearch`: a debounced search box in the app shell top bar. Results
  are grouped by type; clicking one navigates into a filtered view — an
  activity or milestone result searches by title, a team/tag/user result
  filters Admin > Activities by that dimension. This is what makes the
  filter-state-in-the-URL design pay off: no extra plumbing was needed to
  wire search into the filtered views.

**Verified:** 19/19 backend tests pass, frontend type-checks clean, checked
in a browser — "Delayed only" correctly narrows to 2 activities while
leaving the timeline's date range unchanged, and searching "test" then
clicking the "Testing" tag result correctly navigates to
`/admin/activities?tag_id=4` with the FilterBar reflecting the applied
filter.

**Not yet implemented:** filtering by milestone/dependency relationship
(deferred until Phase 5's dependency graph exists), and search doesn't yet
cover comments (comments don't exist until Phase 10).

## Phase 3 — Gantt read-only rendering (2026-09-04)

The primary long-term planning view: a custom-built timeline (no Gantt
library — see the architecture proposal's reasoning) rendering activities
and milestones from live data.

**Backend**
- `GET /milestones` (read-only, `project_id` filter) — needed so the Gantt
  can show milestones alongside activities; full milestone CRUD is still a
  later phase.

**Frontend**
- `components/gantt/dateScale.ts`: pure date-math utilities — pixels-per-day
  per zoom level, ISO 8601 week numbering (Monday-start, week 1 contains the
  year's first Thursday), and month/week header block generation. Kept
  framework-free so it can get real unit tests once a frontend test runner
  is introduced.
- `TimelineHeader`: month/year header row always shown; an ISO week-number
  row shown at Month and Week zoom (suppressed at Quarter/Year, where weekly
  ticks would be unreadably dense).
- `GanttBar`: status-colored bars (not started / in progress / completed /
  delayed / blocked) with a progress-percent fill overlay. Delayed and
  blocked use a diagonal-stripe pattern, not just color, so they read
  clearly even without relying on hue alone.
- `MilestoneMarker`: diamond markers in a dedicated "Milestones" group above
  the team groups.
- `GanttChart`: activities grouped by owner team (sorted by the team's
  `sort_order`, with an "Unassigned" group for activities with no owner
  team), a red current-date line, and Year/Quarter/Month/Week zoom control.
  Frozen header row and frozen row-label column (sticky top/left) so labels
  stay visible while scrolling a timeline that can be much wider than the
  viewport at finer zoom levels.
- No filtering, search, drag-and-drop, or dependency arrows yet — filtering
  is Phase 4, dependencies (including their visualization) are Phase 5, and
  drag-and-drop is explicitly deferred until the scheduling engine exists
  (per the master spec).

**Fixed while building this:** `.app-content` (a flex item) was missing
`min-width: 0`, so a wide Gantt grid expanded the whole page horizontally —
including the sidebar nav scrolling out of view — instead of scrolling
inside its own viewport. This is a common flexbox pitfall (flex items default
to `min-width: auto`, refusing to shrink below their content's intrinsic
width) worth remembering for any other wide-content view added later
(the Calendar week view is a likely candidate).

**Verified:** backend tests pass (13/13), frontend type-checks clean, all
four zoom levels checked in a browser against the seeded data — including
confirming the current-date line lands in ISO week 36 for 4 Sept 2026, which
matches manual calculation, and that horizontal scrolling keeps the sidebar,
header, and row labels correctly pinned in place.

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
