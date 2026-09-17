# Project Schedule (Gantt)

**Route:** `/:projectSlug/gantt`
**Frontend:** `frontend/src/pages/Gantt.tsx` → `frontend/src/components/gantt/GanttChart.tsx`
**Backend:** `GET /activities`, `GET /milestones`, `GET /dependencies`, `POST /scheduling/preview`, `POST /scheduling/apply`, `POST /scheduling/undo`

## Purpose

The main timeline view of the plan: every activity and milestone laid out
against a horizontal date axis, groupable by team, with drag-free date
editing that previews and cascades through dependent items before
anything is saved.

## Crucial functionality

### Filtering
Uses the same `FilterBar` as Admin > Activities (search, team — including
"Organization" — owner, contributor, tag, status, priority, date range,
"Delayed only"/"Blocked only" chips). Filters affect which activities and
milestones are drawn, but the chart's own date range and zoom stay fixed
(computed from the *unfiltered* full activity/milestone set) so narrowing
a filter never rescales the whole chart. A project can configure a default
team/tag filter for this page in Admin > Settings; the URL always wins
over that default once the viewer changes anything.

### Grouping and view modes
- **By Team** (default): one row-group per team (in team `sort_order`),
  then "Organization" for all-teams activities, then "Unassigned".
- **Timeline**: all visible activities flattened into a single group,
  sorted by start date, with the owning team appended to each row's label.

Each group (plus "Milestones" as its own toggleable group) has a
show/hide chip in the "Show groups" bar, plus "Hide all"/"Show all".

### Zoom levels
`Year`, `Quarter`, `Month`, `Week` — changes the pixel-per-day scale and
the timeline header's tick granularity. Milestone label overflow is
recalculated per zoom level so long milestone titles don't get clipped at
the edge of the chart.

### Milestones lane
Milestones render above the activity groups, laid out into overlap-avoiding
lanes so two milestones close in time don't collide. Clicking one (if the
viewer `canManageMilestone` it and the project isn't read-only) opens the
Reschedule modal.

### Activity bars
Each activity renders as a `GanttBar` colored by status (not started / in
progress / completed / delayed / blocked — same palette used everywhere
else in the app). Clicking a bar (if the viewer `canEditActivity` it and
the project isn't read-only) opens the Reschedule modal for that activity.

### Dependency arrows
When dependencies exist, `DependencyArrows` draws connector lines between
related activities/milestones across the whole grid, positioned from the
same row index used for layout.

### Reschedule modal — preview, reason, cascade, undo
This is the page's most important piece of business logic:
1. Pick a new start/end date (a milestone only has one date field).
2. As soon as the date differs from the original, the modal debounces and
   calls `POST /scheduling/preview`, which computes what *else* would move
   if this change were applied — every downstream dependency in the graph,
   shown as a table of item / from / to / day-shift.
3. A **reason is mandatory** before "Apply changes" is enabled — this app's
   standing rule is that dates never change silently.
4. `POST /scheduling/apply` commits the change and the entire cascade
   together as one `change_group_id`, writing an audit-log entry (visible
   in the activity's own history and in the Excel change-log export) for
   every field that changed on every affected item.
5. Immediately after applying, an **Undo** button appears, calling
   `POST /scheduling/undo` with that same `change_group_id` to revert the
   whole cascade atomically — available until the modal is closed.

### PNG / PDF export
- **Export as PNG** rasterizes the currently-rendered grid (`html-to-image`)
  at the current filter/zoom/group-visibility state, using the active
  theme's surface color as the background, and downloads it as
  `<project-slug>-<date>.png`.
- **Print / Save as PDF** calls the browser's native print dialog; print-
  specific CSS (see `index.css`) forces light, high-contrast colors so
  status colors and milestone diamonds stay legible on paper.

### Empty state
If filters are active and produce zero activities *and* zero milestones,
the chart is replaced with "No activities or milestones match these
filters." rather than rendering an empty grid.

## Permissions
- Viewing is available to anyone with project access.
- Rescheduling an activity requires `canEditActivity` (project/team edit
  rights) *and* the project not being read-only; the same applies to
  milestones via `canManageMilestone`. Without those, bars/markers are
  still visible but not clickable.
