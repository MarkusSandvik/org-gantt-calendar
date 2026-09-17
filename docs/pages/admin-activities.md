# Admin > Activities

**Route:** `/:projectSlug/admin/activities`
**Frontend:** `frontend/src/pages/admin/{ActivitiesAdmin,ActivityFormModal}.tsx`
**Backend:** `GET/POST/PATCH/DELETE /activities`, `GET/POST /activities/:id/comments`, `GET /audit-log?entity_type=activity`

## Purpose

The full CRUD table for activities — the same records that render as bars
on the Gantt and slices on the Calendar wheel, but here as an editable,
heavily filterable list with per-field permission enforcement and a full
change history per row.

## Crucial functionality

### Filtering (`FilterBar`, shared with the Gantt page)
Title search, team (**All teams** / **Organization** / a specific team —
"Organization" maps to `all_teams_only=true` server-side, not a `team_id`),
owner, contributor, tag, status, priority, a date range, and two one-click
toggle chips ("Delayed only", "Blocked only"). Filter state lives in the
URL, so a link like `?status=delayed` (used by the Dashboard's metric
badges) opens pre-filtered.

### Table
Title, team ("Organization" for an all-teams activity), owner, status
badge (with a separate **Overdue** flag — end date has passed but the
activity was never marked `delayed` — layered on top of whatever status it
actually has), priority badge, progress %, and dates. Clicking a row opens
it for editing.

### Creating an activity
"New Activity" is shown only to an Admin or a Lead of at least one team
(`canCreateAnywhere`) with edit access to the project. A non-Admin creator
can only choose their own led team(s) as the owner team; only an Admin can
set an activity to apply to the whole Organization.

### Three-tier per-field edit permission
This is the most important nuance on this page — editing rights are not
all-or-nothing:
1. **Full edit** (`canEditActivity`: an Admin, or the Lead of the
   activity's owner team) — every field, including title, dates, owner,
   contributors, tags, and delete.
2. **Assigned-only** (`canUpdateAssignedFieldsOnly`: an owner or
   contributor who isn't a full editor) — can change only **status** and
   **progress %**; every other field is disabled, and a hint explains why.
3. **Read-only** (anyone else, or when the project itself is read-only) —
   the form is entirely disabled but still viewable, including its full
   history.

### Dates lock when dependencies exist
Same rule as Milestones: if the activity has any dependency link, its
start/end dates are disabled here with a pointer to reschedule from the
Gantt page instead, so the cascade impact is previewed before anything
changes.

### Reason required for saved changes
Any save on an *existing* activity (by a full or assigned-only editor)
requires a non-empty "reason for this change" — enforced both client-side
and server-side (`422` without one) — matching the same "never change
silently" rule the Gantt's reschedule flow enforces. Creating a brand-new
activity does not require a reason.

### Activity Log panel
Same combined comment + audit-log timeline described in
[`milestones.md`](./milestones.md) — comments require
`canCommentOnActivity`, audit rows show old → new value per changed field
plus the reason text, and this exact data is what the Excel change-log
export (Admin > Import/Export) pulls from.

## Notes
- This page and the Gantt page share the exact same `FilterBar` and
  `useActivityFilters` — a filter set here (including in the URL) does not
  carry over to the Gantt page automatically; they're independent URLs.
