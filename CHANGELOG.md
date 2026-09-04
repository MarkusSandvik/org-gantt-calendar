# Changelog

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
