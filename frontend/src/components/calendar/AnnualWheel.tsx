import { useState } from "react";
import type { Activity, ActivityStatus, CalendarEvent, CalendarEventType, Team } from "../../api/types";
import { branding } from "../../branding";
import { buildGroups } from "../gantt/activityGroups";
import { daysBetween, formatISODate, parseISODate } from "../../utils/date";

const WIDTH = 1000;
const HEIGHT = 640;
const CENTER_X = WIDTH / 2;
const CENTER_Y = HEIGHT / 2;
const OUTER_RADIUS = 230;
const MONTH_RING_RADIUS = 210;
const MARKER_RADIUS = 175;
const PIE_RADIUS = 158;
const HUB_RADIUS = 34;
const HUB_ICON_RADIUS = 24;
const DAYS_IN_WHEEL = 365;
// "Coming three weeks" for the near-term-only detail filter — an option to
// declutter the label set down to what's actually imminent, independent of
// the pie slices/dots themselves (those always cover the full year).
const DETAIL_WINDOW_DAYS = 21;

// Where leader lines terminate and label text begins, on each side of the
// wheel — far enough past the ring that a line from any marker to any
// label reads clearly, with the remaining width up to the canvas edge left
// for the text itself (right-growing on the right side, left-growing/
// right-aligned on the left).
const LABEL_GAP = 30;
const LABEL_X_RIGHT = CENTER_X + OUTER_RADIUS + LABEL_GAP;
const LABEL_X_LEFT = CENTER_X - OUTER_RADIUS - LABEL_GAP;
const LABEL_MAX_CHARS = 30;

// A label's full text (title + team + status/date) can run well past the
// ~240px gap between the ring and the canvas edge that the base WIDTH
// leaves free. The SVG root clips anything outside its viewBox by default,
// which used to cut long left-side labels off mid-word. Padding the
// viewBox left/right (without touching CENTER_X, so the wheel itself
// doesn't move) gives labels the room to render in full instead.
const LABEL_CANVAS_PAD = 220;
const VIEW_X_MIN = -LABEL_CANVAS_PAD;
const VIEW_WIDTH = WIDTH + LABEL_CANVAS_PAD * 2;

// The vertical band labels are allowed to occupy — kept inside the canvas
// and clear of the "Today" callout above the ring.
const LABEL_TOP_BOUND = CENTER_Y - OUTER_RADIUS + 12;
const LABEL_BOTTOM_BOUND = CENTER_Y + OUTER_RADIUS - 4;
const MIN_LABEL_SPACING = 16;

// Mirrors the .event-chip--<type> background colors in index.css — SVG
// shapes don't pick those up via class (the CSS rule sets `background`,
// which only applies to boxes), so the same hex values are duplicated
// here for the wheel's markers, leader lines, and legend.
const EVENT_TYPE_COLORS: Record<CalendarEventType, string> = {
  meeting: "#2f6fed",
  social: "#d1459e",
  deadline: "#d1453b",
  workshop: "#7c3aed",
  recruitment: "#21a35f",
  sponsor: "#e08a1e",
  travel: "#0891b2",
  presentation: "#4f46e5",
  stand_duty: "#6b7280",
  other: "#9aa1ab",
};

const EVENT_TYPE_ORDER: CalendarEventType[] = [
  "meeting",
  "social",
  "deadline",
  "workshop",
  "recruitment",
  "sponsor",
  "travel",
  "presentation",
  "stand_duty",
  "other",
];

// Mirrors the .gantt-bar--<status> colors in index.css (the striped
// delayed/blocked patterns there are flattened to their solid accent here —
// stripes don't carry over cleanly to a thin ring segment).
const ACTIVITY_STATUS_COLORS: Record<ActivityStatus, string> = {
  not_started: "var(--color-track-empty)",
  in_progress: "#2f6fed",
  completed: "#21a35f",
  delayed: "#e08a1e",
  blocked: "#d1453b",
};
const ACTIVITY_STATUS_ORDER: ActivityStatus[] = [
  "not_started",
  "in_progress",
  "completed",
  "delayed",
  "blocked",
];

// Just two colors that alternate across activities in date order — purely
// to tell adjacent slices apart at a glance, not to encode team or
// anything else (the wheel is normally viewed one team at a time via its
// own filter, so per-team colors would mostly render as one solid color
// anyway). Sourced from CSS custom properties (defined in index.css, with
// an organization-specific override possible in that org's theme file —
// see vortex.css) rather than hardcoded here, so each organization can
// tune the pair to its own brand. Whatever hues an org picks must still
// avoid blue/green/orange/red: those are exactly the four non-gray
// ACTIVITY_STATUS_COLORS above, and a slice sits right next to that same
// activity's status-colored square in this same diagram, so reusing one
// of those hues here would risk being read as a status.
const SLICE_CYCLE_COLORS = ["var(--color-wheel-slice-1)", "var(--color-wheel-slice-2)"];

const MONTH_NAMES = Array.from({ length: 12 }, (_, i) =>
  new Intl.DateTimeFormat("en-GB", { month: "short" }).format(new Date(2000, i, 1)),
);
const LABEL_DATE_FORMAT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });

/** Position for `daysFromToday` (0..364) on a circle where day 0 (today)
 * is fixed at the top and later days proceed clockwise. */
function pointForDay(daysFromToday: number, radius: number): { x: number; y: number } {
  const angle = (daysFromToday / DAYS_IN_WHEEL) * 2 * Math.PI;
  return {
    x: CENTER_X + radius * Math.sin(angle),
    y: CENTER_Y - radius * Math.cos(angle),
  };
}

function truncate(title: string, maxChars: number = LABEL_MAX_CHARS): string {
  return title.length > maxChars ? `${title.slice(0, maxChars - 1)}…` : title;
}

/** A filled pie slice from the center out to `radius`, spanning `startDay`
 * to `endDay` (exclusive), drawn clockwise to match pointForDay's
 * convention. */
function describeSlice(startDay: number, endDay: number, radius: number): string {
  const start = pointForDay(startDay, radius);
  const end = pointForDay(endDay, radius);
  const largeArc = endDay - startDay > DAYS_IN_WHEEL / 2 ? 1 : 0;
  return `M ${CENTER_X} ${CENTER_Y} L ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y} Z`;
}

/** The [start, end) day ranges NOT covered by any of the given (already
 * sorted-by-start) intervals — i.e. the stretches of the year with no
 * planned activity at all, so they can be filled in with their own color
 * rather than just showing whatever happens to be behind the wheel. */
function findGaps(intervals: { clippedStart: number; clippedEnd: number }[]): [number, number][] {
  const sorted = [...intervals].sort((a, b) => a.clippedStart - b.clippedStart);
  const gaps: [number, number][] = [];
  let cursor = 0;
  for (const { clippedStart, clippedEnd } of sorted) {
    if (clippedStart > cursor) gaps.push([cursor, clippedStart]);
    cursor = Math.max(cursor, clippedEnd);
  }
  if (cursor < DAYS_IN_WHEEL) gaps.push([cursor, DAYS_IN_WHEEL]);
  return gaps;
}

type WheelLabel = {
  id: string;
  anchor: { x: number; y: number };
  side: "left" | "right";
  labelY: number;
  color: string;
  shape: "circle" | "square";
  text: string;
  dateText: string;
  onClick?: () => void;
};

/** Greedy top-to-bottom separation: labels keep their natural (anchor)
 * height whenever there's room, and only get pushed down just enough to
 * clear the one above when two dates land too close together to fit side
 * by side. If the last label would run past the bottom of the wheel, a
 * second pass pulls everything back up by the same rule, so overflow is
 * shared across the whole column instead of clipping only the final
 * entries. */
function separate(labels: WheelLabel[]): void {
  labels.sort((a, b) => a.anchor.y - b.anchor.y);
  for (let i = 0; i < labels.length; i++) {
    const min = i === 0 ? LABEL_TOP_BOUND : labels[i - 1].labelY + MIN_LABEL_SPACING;
    labels[i].labelY = Math.max(labels[i].anchor.y, min);
  }
  const overflow = labels.length > 0 ? labels[labels.length - 1].labelY - LABEL_BOTTOM_BOUND : 0;
  if (overflow > 0) {
    for (let i = labels.length - 1; i >= 0; i--) {
      const max = i === labels.length - 1 ? LABEL_BOTTOM_BOUND : labels[i + 1].labelY - MIN_LABEL_SPACING;
      labels[i].labelY = Math.min(labels[i].labelY, max);
    }
  }
}

interface AnnualWheelProps {
  today: Date;
  events: CalendarEvent[];
  activities: Activity[];
  teams: Team[];
  onEventClick: (event: CalendarEvent) => void;
}

export function AnnualWheel({ today: rawToday, events, activities, teams, onEventClick }: AnnualWheelProps) {
  const [showActivityDetails, setShowActivityDetails] = useState(true);
  const [nearTermOnly, setNearTermOnly] = useState(false);

  // Normalized to midnight so day-math below (daysBetween against
  // midnight-based event dates) can't round off by one depending on the
  // time of day this renders.
  const today = new Date(rawToday.getFullYear(), rawToday.getMonth(), rawToday.getDate());
  const todayKey = formatISODate(today);

  const monthTicks = Array.from({ length: 13 }, (_, i) => {
    const monthStart = new Date(today.getFullYear(), today.getMonth() + i, 1);
    return { date: monthStart, daysFromToday: daysBetween(today, monthStart) };
  }).filter((t) => t.daysFromToday >= 0 && t.daysFromToday < DAYS_IN_WHEEL);

  // Every activity is a full pie slice sharing the same radius — teams
  // aren't separated into their own rings. Overlap between activities
  // (from the same team or different ones) is resolved purely by paint
  // order: sorted globally by start_date ascending and rendered in that
  // order, so a later-starting activity's slice covers an earlier one
  // wherever their date ranges overlap, per the "latest start wins" rule.
  // buildGroups is only used for the team label shown in tooltips/labels;
  // slice color cycles by position in the global sort instead (see
  // SLICE_CYCLE_COLORS above).
  const teamLabelByActivityId = new Map<number, string>();
  for (const group of buildGroups(activities, teams)) {
    for (const activity of group.activities) {
      teamLabelByActivityId.set(activity.id, group.label);
    }
  }
  const clippedActivities = activities
    .map((activity) => {
      const startDay = daysBetween(today, parseISODate(activity.start_date));
      // +1 so a single-day activity still draws a visible sliver,
      // matching GanttBar's own end-date-is-inclusive convention.
      const endDay = daysBetween(today, parseISODate(activity.end_date)) + 1;
      return {
        activity,
        teamLabel: teamLabelByActivityId.get(activity.id) ?? "Unassigned",
        clippedStart: Math.max(startDay, 0),
        clippedEnd: Math.min(endDay, DAYS_IN_WHEEL),
      };
    })
    .filter(({ clippedStart, clippedEnd }) => clippedEnd > clippedStart)
    .sort((a, b) => a.activity.start_date.localeCompare(b.activity.start_date))
    .map((item, index) => ({ ...item, color: SLICE_CYCLE_COLORS[index % SLICE_CYCLE_COLORS.length] }));

  const noActivityGaps = findGaps(clippedActivities);

  const eventLabels: WheelLabel[] = events
    .map((event) => {
      const dateKey = event.start_datetime.slice(0, 10);
      const daysFromToday = daysBetween(today, new Date(dateKey + "T00:00:00"));
      return { event, daysFromToday };
    })
    .filter((p) => p.daysFromToday >= 0 && p.daysFromToday < DAYS_IN_WHEEL)
    .filter((p) => !nearTermOnly || p.daysFromToday < DETAIL_WINDOW_DAYS)
    .map(({ event, daysFromToday }) => {
      const anchor = pointForDay(daysFromToday, MARKER_RADIUS);
      return {
        id: `event-${event.id}`,
        anchor,
        side: (anchor.x >= CENTER_X ? "right" : "left") as "left" | "right",
        labelY: anchor.y,
        color: EVENT_TYPE_COLORS[event.event_type],
        shape: "circle" as const,
        text: truncate(event.title),
        dateText: LABEL_DATE_FORMAT.format(new Date(event.start_datetime)),
        onClick: () => onEventClick(event),
      };
    });

  const activityLabels: WheelLabel[] = showActivityDetails
    ? clippedActivities
        .filter(({ clippedStart }) => !nearTermOnly || clippedStart < DETAIL_WINDOW_DAYS)
        .map(({ activity, teamLabel, clippedStart, clippedEnd }) => {
          const midDay = (clippedStart + clippedEnd) / 2;
          const anchor = pointForDay(midDay, MARKER_RADIUS);
          return {
            id: `activity-${activity.id}`,
            anchor,
            side: (anchor.x >= CENTER_X ? "right" : "left") as "left" | "right",
            labelY: anchor.y,
            color: ACTIVITY_STATUS_COLORS[activity.status],
            shape: "square" as const,
            text: `${truncate(activity.title, 22)} · ${teamLabel}`,
            dateText: activity.status.replace("_", " "),
          };
        })
    : [];

  const allLabels = [...eventLabels, ...activityLabels];
  const rightLabels = allLabels.filter((l) => l.side === "right");
  const leftLabels = allLabels.filter((l) => l.side === "left");
  separate(rightLabels);
  separate(leftLabels);

  return (
    <div className="annual-wheel">
      <div className="annual-wheel__toolbar">
        <button
          type="button"
          className="button"
          onClick={() => setNearTermOnly((v) => !v)}
        >
          {nearTermOnly ? "Show full year" : `Show next ${DETAIL_WINDOW_DAYS / 7} weeks only`}
        </button>
        <button
          type="button"
          className="button"
          onClick={() => setShowActivityDetails((v) => !v)}
        >
          {showActivityDetails ? "Hide" : "Show"} activity details
        </button>
      </div>

      <svg
        viewBox={`${VIEW_X_MIN} 0 ${VIEW_WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Annual wheel of planned events and activities, starting today (${todayKey})`}
      >
        <defs>
          {/* A hatch pattern, not a solid color, for "no planned activity" —
              guaranteed distinct from any status/type color regardless of
              which organization's theme is active, rather than picking a
              specific shade that might turn out close to one of theirs. */}
          <pattern
            id="annual-wheel-empty-pattern"
            width="6"
            height="6"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="6" height="6" className="annual-wheel__no-activity-pattern-bg" />
            <line x1="0" y1="0" x2="0" y2="6" className="annual-wheel__no-activity-pattern-line" />
          </pattern>
        </defs>

        <circle cx={CENTER_X} cy={CENTER_Y} r={OUTER_RADIUS} className="annual-wheel__ring" />

        {noActivityGaps.map(([gapStart, gapEnd]) => (
          <path
            key={`gap-${gapStart}`}
            d={describeSlice(gapStart, gapEnd, PIE_RADIUS)}
            className="annual-wheel__no-activity"
          />
        ))}

        {clippedActivities.map(({ activity, teamLabel, color, clippedStart, clippedEnd }) => {
          const tooltip = `${activity.title} — ${teamLabel} · ${activity.status.replace("_", " ")} · ${activity.start_date} → ${activity.end_date}`;
          return (
            <path
              key={activity.id}
              d={describeSlice(clippedStart, clippedEnd, PIE_RADIUS)}
              style={{ fill: color }}
              className="annual-wheel__activity-slice"
            >
              <title>{tooltip}</title>
            </path>
          );
        })}

        <circle cx={CENTER_X} cy={CENTER_Y} r={HUB_RADIUS} className="annual-wheel__hub" />
        {branding.iconHref && (
          <image
            href={branding.iconHref}
            x={CENTER_X - HUB_ICON_RADIUS}
            y={CENTER_Y - HUB_ICON_RADIUS}
            width={HUB_ICON_RADIUS * 2}
            height={HUB_ICON_RADIUS * 2}
            aria-hidden="true"
          />
        )}

        {monthTicks.map(({ date, daysFromToday }) => {
          const inner = pointForDay(daysFromToday, MONTH_RING_RADIUS - 10);
          const outer = pointForDay(daysFromToday, OUTER_RADIUS);
          const labelPos = pointForDay(daysFromToday + 15, MONTH_RING_RADIUS);
          return (
            <g key={formatISODate(date)}>
              <line
                x1={inner.x}
                y1={inner.y}
                x2={outer.x}
                y2={outer.y}
                className="annual-wheel__month-tick"
              />
              <text x={labelPos.x} y={labelPos.y} className="annual-wheel__month-label">
                {MONTH_NAMES[date.getMonth()]}
              </text>
            </g>
          );
        })}

        {[...rightLabels, ...leftLabels].map((label) => {
          const labelX = label.side === "right" ? LABEL_X_RIGHT : LABEL_X_LEFT;
          return (
            <g
              key={label.id}
              className={
                "annual-wheel__label-group" + (label.onClick ? " annual-wheel__label-group--clickable" : "")
              }
              onClick={label.onClick}
            >
              <path
                d={`M ${label.anchor.x} ${label.anchor.y} L ${labelX} ${label.labelY}`}
                className="annual-wheel__leader"
                style={{ stroke: label.color }}
              />
              {label.shape === "circle" ? (
                <circle
                  cx={label.anchor.x}
                  cy={label.anchor.y}
                  r={6}
                  fill={label.color}
                  className="annual-wheel__marker"
                />
              ) : (
                <rect
                  x={label.anchor.x - 5}
                  y={label.anchor.y - 5}
                  width={10}
                  height={10}
                  fill={label.color}
                  className="annual-wheel__marker"
                />
              )}
              <text
                x={labelX + (label.side === "right" ? 6 : -6)}
                y={label.labelY}
                textAnchor={label.side === "right" ? "start" : "end"}
                className="annual-wheel__label-text"
              >
                {label.text}
                <tspan className="annual-wheel__label-text-detail"> · {label.dateText}</tspan>
              </text>
            </g>
          );
        })}

        <line
          x1={CENTER_X}
          y1={CENTER_Y - OUTER_RADIUS - 14}
          x2={CENTER_X}
          y2={CENTER_Y - OUTER_RADIUS + 14}
          className="annual-wheel__today-marker"
        />
        <text x={CENTER_X} y={CENTER_Y - OUTER_RADIUS - 20} className="annual-wheel__today-label">
          Today · {todayKey}
        </text>
      </svg>

      <div className="annual-wheel__legend">
        <span className="annual-wheel__legend-group">
          {EVENT_TYPE_ORDER.map((type) => (
            <span key={type} className="annual-wheel__legend-item">
              <span
                className="annual-wheel__legend-swatch"
                style={{ background: EVENT_TYPE_COLORS[type] }}
              />
              {type.replace("_", " ")}
            </span>
          ))}
        </span>
        <span className="annual-wheel__legend-group">
          {ACTIVITY_STATUS_ORDER.map((status) => (
            <span key={status} className="annual-wheel__legend-item">
              <span
                className="annual-wheel__legend-swatch annual-wheel__legend-swatch--square"
                style={{ background: ACTIVITY_STATUS_COLORS[status] }}
              />
              {status.replace("_", " ")}
            </span>
          ))}
          <span className="annual-wheel__legend-item">
            <span className="annual-wheel__legend-swatch annual-wheel__legend-swatch--square annual-wheel__legend-swatch--pattern" />
            no planned activity
          </span>
        </span>
      </div>
    </div>
  );
}
