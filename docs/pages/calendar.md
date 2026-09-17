# Calendar

**Routes:** `/:projectSlug/calendar` (redirects to Month), `/calendar/month/:year/:month`, `/calendar/week/:isoYear/:isoWeek`, `/calendar/year`, `/calendar/year/:year`, `/calendar/wheel`
**Frontend:** `frontend/src/pages/calendar/{CalendarMonthPage,CalendarWeekPage,CalendarYearPage,CalendarWheelPage}.tsx`, `frontend/src/components/calendar/*`
**Backend:** `GET/POST/PATCH/DELETE /calendar-events`

## Purpose

Scheduling and events for the project — meetings, deadlines, social events,
travel, etc. — as distinct from the Gantt's activities/milestones, though
the two can be cross-linked. Four interchangeable views over the same
underlying event data, switched via the tab bar at the top of every
Calendar page (Week / Month / Year / Wheel).

## Shared across every view

### Team/tag filtering
`CalendarFilterBar` + `useCalendarFilters` — a team selector (blank = no
filter, **Organization** = only `all_teams` events, or a specific team)
and a tag selector, both reflected in the events query
(`all_teams_only`/`team_id`/`tag_id` params). A project can configure a
default team/tag for Calendar in Admin > Settings (`default_calendar_*`
fields) — the wheel view is the main reason this default exists, since it
is most useful pinned to "Organization".

### Event modal (create/edit)
One shared `CalendarEventModal` across all four views:
- Title, description, type (`meeting`/`social`/`deadline`/`workshop`/
  `recruitment`/`sponsor`/`travel`/`presentation`/`stand_duty`/`other` —
  each with its own color used consistently everywhere events render),
  all-day toggle, start/end (date-only when all-day, otherwise
  datetime-local), location.
- Team (**Organization** is only offered as an option to Admins — see
  `can_apply_to_all_teams`), owner user, an optional **related activity**
  link (drawn from the full unfiltered activity list, independent of
  whatever the Calendar's own team filter is currently scoped to), and
  tags.
- **Recurrence** (creation only, not shown when editing an existing
  event): Does not repeat / Daily / Weekly / Biweekly / Monthly, with a
  required end date. Submitting materializes one row per occurrence up to
  that end date, all sharing a `recurrence_group_id`.
- Read-only projects disable every field but still let you open an event
  to view its details.

### Deleting an event
Two confirms in sequence (`confirmDeleteCalendarEvent`): first a plain
"Delete this event?", then — only if the event belongs to a recurring
series — a second choice between deleting just this occurrence or this
occurrence **and every future one** in the series (past occurrences are
never touched).

## Month view
Traditional month grid (`MonthGrid`). Prev/Today/Next navigation. Clicking
an empty day (if editable) opens the "new event" modal defaulted to that
date; clicking an event opens it for editing; clicking a week number jumps
to that ISO week in Week view.

## Week view
Seven day-columns (Monday–Sunday) listing that day's events as colored
chips (time-prefixed unless all-day). A second panel, **Running project
activities**, lists every Gantt activity whose date range overlaps the
week (independent of the Calendar's own team filter), each with its
status badge, priority badge, and progress percent — a quick "what's
actually in flight this week" cross-reference between Calendar and Gantt.

## Year view
Twelve compact month grids. Days with at least one event are highlighted
and show event titles on hover; today is highlighted separately. Clicking
any day or the month header jumps into Month view for that month.

## Annual Wheel view
A circular, rotating visualization — see the in-depth description below.
This is the newest and most distinctive of the four views.

### Layout
A 365-day ring starting from **today at 12 o'clock**, running clockwise,
re-centered every time the page loads (it is not a fixed calendar year).
Twelve month tick labels run around the ring's edge.

### Two layers of information
1. **Calendar events** — plotted as colored dot markers at their date,
   colored by event type.
2. **Activities** (from the Gantt) — plotted as a true pie chart filling
   the inside of the ring: one wedge per activity from its start to end
   date. Overlapping activities are resolved purely by z-order — whichever
   activity **started later** paints on top — matching the same
   overlap rule used nowhere else in the app; this is deliberate, not a
   rendering accident. Slice color cycles through a small, org-themeable
   two-color palette (`--color-wheel-slice-1/2`, overridable per
   organization in its theme file) purely to separate adjacent wedges —
   it carries no team or status meaning. A day range with zero planned
   activity is filled with a diagonal hatch pattern rather than a solid
   color, so it can never be mistaken for a real (if oddly-colored)
   activity.

The wheel's activity set respects the **same team filter as the rest
of the Calendar page** — switching to a specific team narrows the pie
to that team's activities only, filtered client-side from the full
activity list (there is no dedicated backend endpoint for this).

### Detail labels
Every event dot and activity wedge can show a text label (title, team,
status/date) connected by a leader line, laid out with a collision-
avoidance algorithm so labels never visually overlap regardless of how
many items land close together in time. Two independent controls:
- **Hide/Show activity details** — toggles the activity labels only (the
  wedges themselves always render).
- **Show next 3 weeks only / Show full year** — restricts *which* labels
  (both events and activities) are shown to the coming three weeks, since
  that window always falls in the readable region near the top of the
  wheel; the underlying wedges/dots for the full year are unaffected.

### Center hub
A themeable circular hub in the middle of the wheel. If the active
organization's branding profile defines an `iconHref` (a mark-only logo,
no wordmark text), it renders there — e.g. Vortex NTNU's icon.

### Interacting with the wheel
Clicking an event dot opens it in the same edit modal used by the other
views. "New Event" is also available and defaults the new event's date to
today (the wheel has no concept of "the day you clicked" the way a grid
does). Activity wedges are not clickable — reschedule activities from the
Gantt page.

## Notes
- All four views share the same `CalendarEvent` data — there's no
  per-view data model, only different renderings of the same query.
