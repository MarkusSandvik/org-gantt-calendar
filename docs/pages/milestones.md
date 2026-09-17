# Milestones

**Route:** `/:projectSlug/milestones`
**Frontend:** `frontend/src/pages/milestones/{MilestonesPage,MilestoneFormModal}.tsx`
**Backend:** `GET/POST/PATCH/DELETE /milestones`, `GET/POST /milestones/:id/comments`, `GET /audit-log?entity_type=milestone`

## Purpose

A flat, filterable list of every milestone in the project — the same
milestones that appear as diamonds on the Gantt's milestone lane, but as a
sortable table with full edit/comment/history access per row.

## Crucial functionality

### Filtering
Team (plain dropdown — **note: unlike Admin > Activities/Gantt, this
list's team filter has no "Organization" option**, so there is currently
no way to filter this table down to only all-teams milestones), status
(`not_started`/`on_track`/`at_risk`/`completed`/`missed`), and a title
search box. On first load the team filter is seeded from the project's
Gantt default-view team (Admin > Settings) rather than a separate
milestones-specific setting — it never re-applies once the viewer changes
it themselves.

### List and row click
A table (title, date, team — "Organization" for an all-teams milestone,
owner, status badge, tags). Clicking any row opens it in the edit modal.
"New Milestone" is shown only to an Admin or a team Lead (`canCreateAnywhere`)
with edit access to the project.

### Milestone form
Title, description, date, status, team (**Organization** is offered only
to Admins), owner, tags, and an optional free-text "reason for this
change" note shown only when editing (not required, unlike an Activity's
reason field).

### Date is locked when dependencies exist
If a milestone participates in any dependency, its date field is disabled
in this modal with a hint pointing to the Gantt page — rescheduling a
milestone with dependents must go through the Reschedule modal there
(`POST /scheduling/preview` → `/apply`) so the cascade impact on dependent
items is shown and confirmed before anything changes, rather than being
silently editable here.

### Permissions
- Creating requires `isAdmin || isLeadOfAnyTeam` and the project being
  editable.
- Editing an *existing* milestone additionally requires
  `canManageMilestone` for that specific milestone (its own team's Lead,
  or an Admin) — a viewer without that right can still open it to read
  its details and history, just not change or delete it.
- A read-only project disables editing entirely regardless of role.

### Activity Log panel (inside the edit modal)
A combined, chronologically merged timeline of:
- **Comments** — free-text notes anyone with `canCommentOnMilestone`
  rights can add ("Add note"); a comment can also carry a status-change
  annotation when it was left as part of changing the milestone's status.
- **Audit log entries** — one row per field actually changed (date,
  status, team, owner, etc.), each showing old → new value (team/user ids
  resolved to names) and the optional reason text, sourced from the same
  `AuditLog` table used by the Excel change-log export.

## Notes
- Milestone status is a distinct enum from Activity status
  (`not_started`/`on_track`/`at_risk`/`completed`/`missed` vs. the
  Activity's `not_started`/`in_progress`/`completed`/`delayed`/`blocked`)
  — the two are not interchangeable even though the badges look similar.
