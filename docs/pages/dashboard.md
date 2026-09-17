# Dashboard

**Route:** `/:projectSlug` (project index route)
**Frontend:** `frontend/src/pages/Dashboard.tsx`
**Backend:** `GET /dashboard/summary?project_id=` — `app/services/dashboard.py`

## Purpose

The landing page for a project. Gives a one-screen, current-week snapshot of
what needs attention, rather than requiring a trawl through the Gantt,
Calendar, and Admin pages separately.

## Crucial functionality

### Week metrics strip
A row of clickable count badges, one per non-zero metric for the current
ISO week (Monday–Sunday). Each links directly into the filtered view that
explains the number:

| Metric | Meaning | Links to |
|---|---|---|
| Active tasks | Activities with status `in_progress` (project-wide, not just this week) | Admin > Activities filtered to `in_progress` |
| Milestones | Milestones due Mon–Sun this week | Milestones page |
| Delayed | Activities with status `delayed` (project-wide) | Admin > Activities filtered to `delayed` |
| Blocked | Activities with status `blocked` (project-wide) | Admin > Activities filtered to `blocked` |
| Overdue, not marked | Activities past `end_date`, status not `completed`/`delayed` — the "overdue but not flagged" gap | Admin > Activities (unfiltered) |
| Social activities | Calendar events of type `social` overlapping this week | Calendar week view |
| Meetings | Calendar events of type `meeting` overlapping this week | Calendar week view |
| Upcoming deadline | Calendar events of type `deadline` overlapping this week | Calendar week view |

A metric with a count of 0 is hidden entirely — if nothing is notable, the
strip is replaced with "Nothing notable this week."

### Upcoming Milestones
Lists up to 5 milestones with a due date today or later, excluding ones
already `completed` or `missed`, ordered by date. Each row shows the
milestone's team (or "Organization" for an all-teams milestone).

### Attention Required
A single combined, clickable list built from three activity buckets, in
this order: **delayed** activities (each showing days-late), **blocked**
activities (each showing a best-effort reason — "Blocked by `<predecessor
title>`" when a dependency graph explains it, otherwise just "Blocked"),
then **overdue-but-unflagged** activities (past end date, not marked
completed or delayed). Clicking a row navigates to Admin > Activities
pre-filtered by the activity's title via the search box.

### This Week's Schedule
A Monday–Friday mini-calendar showing every calendar event (any type)
scheduled that day, rendered as the same colored "event chip" style used on
the full Calendar pages. Purely a preview — clicking a chip does nothing;
use the Calendar page to edit events.

## Notes
- Everything on this page is scoped to the active project (from
  `ProjectContext`) — switching projects re-fetches all of it.
- All data is read-only from this page; there is no way to create or edit
  activities, milestones, or events here.
