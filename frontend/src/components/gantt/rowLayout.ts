import type { Activity, Milestone } from "../../api/types";
import { addDays, dateToX, parseISODate, type ZoomLevel } from "./dateScale";

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
    for (const m of milestones) {
      const x = dateToX(parseISODate(m.date), rangeStart, zoom);
      positions.set(`milestone-${m.id}`, { y, startX: x, endX: x });
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
