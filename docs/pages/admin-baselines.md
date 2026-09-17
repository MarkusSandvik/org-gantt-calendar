# Admin > Baselines

**Route:** `/:projectSlug/admin/baselines`
**Frontend:** `frontend/src/pages/admin/{BaselinesAdmin,BaselineFormModal}.tsx`
**Backend:** `GET/POST /baselines`, `GET /baselines/:id/comparison`

## Purpose

"Plan vs. actual" tracking: snapshot every activity's and milestone's
currently planned dates at a point in time, then later see how far the
live plan has drifted from that snapshot.

## Crucial functionality

### Setting a baseline
"Set Baseline" opens a small form (name — defaulted to "Baseline — `<today's
date>`", editable; optional free-text note) and, on submit, captures the
start/end (or single date, for milestones) of **every** activity and
milestone in the project at that exact moment. Baselines are **write-once
and permanent** — there is no edit or delete endpoint; a mistaken or
outdated baseline simply stays in the list forever alongside newer ones.

### Comparing against a baseline
Clicking a baseline row loads its comparison table: every item's baseline
date(s) vs. its current date(s), and the resulting drift in days
(color-coded — later than planned, earlier than planned, or unchanged).
An item created *after* the baseline was taken has nothing to compare
against and won't appear in that baseline's comparison at all.

## Permissions
Creating a baseline requires `canManageBaselines` (Admin-only) and the
project being editable; viewing the list and running comparisons is
available to anyone with project access.

## Notes
- A baseline is a pure snapshot — setting one has no effect on the live
  plan, doesn't lock anything, and doesn't interact with the Gantt's
  reschedule/cascade logic in any way.
