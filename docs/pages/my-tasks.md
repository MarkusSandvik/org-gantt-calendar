# My Tasks

**Route:** `/:projectSlug/my-tasks`
**Frontend:** `frontend/src/pages/MyTasks.tsx`
**Backend:** `GET /activities` (by `owner_user_id`/`contributor_user_id`), `GET /milestones` (by `owner_user_id`), `GET /calendar-events` (by `owner_user_id`, future only)

## Purpose

A personal, read-only "what's mine" view — everything across Activities,
Milestones, and Calendar events that the signed-in user is personally
tied to in the active project, with no filtering controls of its own
(there is nothing to configure; it always reflects "me, right now").

## Crucial functionality

### My Activities
The union of activities where the current user is either the **owner** or
a **contributor** (two separate queries merged and de-duplicated by id),
sorted by end date. Every status/priority/progress is shown, unfiltered by
status — completed activities remain listed here indefinitely. Clicking a
row navigates to Admin > Activities pre-filtered by that activity's title.

### My Milestones
Milestones where the current user is the **owner**, excluding any already
`completed` or `missed`, sorted by date ascending — this section is
deliberately an "outstanding work" list, not a full history.

### My Upcoming Events
Calendar events where the current user is the **owner**, restricted to
`date_from = today` onward (no past events), sorted chronologically.

## Notes
- All three sections are scoped to the active project only — switching
  projects re-fetches everything, and there is no cross-project rollup.
- This page has no create/edit affordances of its own; every row is a
  read-only summary that hands off to the relevant page (Admin >
  Activities, Milestones, Calendar) for actually making changes.
- "Contributor" only affects the Activities section — milestones and
  calendar events only have a single owner field, no contributor list.
