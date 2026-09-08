import type { Activity, Milestone } from "../../api/types";
import { addDays, dateToX, parseISODate, PIXELS_PER_DAY, type ZoomLevel } from "./dateScale";

/** Must stay in sync with the CSS row/group-header heights — the layout is
 * computed here rather than measured from the DOM so arrow positions can be
 * derived synchronously alongside the row JSX, without a measurement pass. */
export const ROW_HEIGHT = 32;
export const GROUP_HEADER_HEIGHT = 24;

export interface RowPosition {
  y: number;
  startX: number;
  endX: number;
}

const MILESTONE_DIAMOND_WIDTH = 12;
const MILESTONE_LABEL_GAP = 6;
const MILESTONE_CHAR_WIDTH = 6.5; // rough average for the 11px label font
const MILESTONE_MIN_GAP = 12; // breathing room required between two markers

function estimateMilestoneWidth(title: string): number {
  return MILESTONE_DIAMOND_WIDTH + MILESTONE_LABEL_GAP + title.length * MILESTONE_CHAR_WIDTH;
}

/** How many extra days of date-range padding a milestone's rendered
 * diamond+label needs past its own date, so its label text isn't clipped by
 * a Gantt (or its PNG export) whose date range ends right at — or just
 * after — that milestone's date. Reuses the same estimated pixel width as
 * lane-packing above, converted to days at the given zoom level. */
export function estimateMilestoneOverflowDays(title: string, zoom: ZoomLevel): number {
  return Math.ceil(estimateMilestoneWidth(title) / PIXELS_PER_DAY[zoom]);
}

/** Packs milestones into as few horizontal lines as possible so their
 * diamond+label markers never overlap: sorted by date, each milestone goes
 * on the first existing line whose last marker's estimated right edge (plus
 * a small buffer) already clears this one's x — otherwise it starts a new
 * line. Label width is estimated from character count rather than measured
 * from the DOM, matching how the rest of this file computes layout
 * synchronously without a measurement pass; it won't be pixel-perfect for
 * every font, but is close enough to catch the overlaps that matter. */
export function assignMilestoneLanes(
  milestones: Milestone[],
  rangeStart: Date,
  zoom: ZoomLevel,
): Milestone[][] {
  const sorted = [...milestones].sort((a, b) => a.date.localeCompare(b.date));
  const lanes: Milestone[][] = [];
  const laneRightEdge: number[] = [];

  for (const m of sorted) {
    const x = dateToX(parseISODate(m.date), rangeStart, zoom);
    const laneIndex = laneRightEdge.findIndex(
      (rightEdge) => x >= rightEdge + MILESTONE_MIN_GAP,
    );
    if (laneIndex === -1) {
      lanes.push([m]);
      laneRightEdge.push(x + estimateMilestoneWidth(m.title));
    } else {
      lanes[laneIndex].push(m);
      laneRightEdge[laneIndex] = x + estimateMilestoneWidth(m.title);
    }
  }

  return lanes;
}

/** Row-position index keyed by "activity-<id>" / "milestone-<id>", built by
 * walking the same milestones + team-group structure the Gantt renders, in
 * the same order, so a dependency arrow can be drawn between any two rows
 * (activity or milestone) regardless of which group they fall in. */
export function buildRowIndex(
  milestones: Milestone[],
  groups: { activities: Activity[] }[],
  rangeStart: Date,
  zoom: ZoomLevel,
): { positions: Map<string, RowPosition>; totalHeight: number } {
  const positions = new Map<string, RowPosition>();
  let y = 0;

  if (milestones.length > 0) {
    y += GROUP_HEADER_HEIGHT;
    for (const lane of assignMilestoneLanes(milestones, rangeStart, zoom)) {
      for (const m of lane) {
        const x = dateToX(parseISODate(m.date), rangeStart, zoom);
        positions.set(`milestone-${m.id}`, { y, startX: x, endX: x });
      }
      y += ROW_HEIGHT;
    }
  }

  for (const group of groups) {
    y += GROUP_HEADER_HEIGHT;
    for (const activity of group.activities) {
      const startX = dateToX(parseISODate(activity.start_date), rangeStart, zoom);
      const endX = dateToX(addDays(parseISODate(activity.end_date), 1), rangeStart, zoom);
      positions.set(`activity-${activity.id}`, { y, startX, endX });
      y += ROW_HEIGHT;
    }
  }

  return { positions, totalHeight: y };
}
