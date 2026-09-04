import { addDays, daysBetween, getISOWeek } from "../../utils/date";

export { addDays, daysBetween, getISOWeek, parseISODate } from "../../utils/date";

export type ZoomLevel = "year" | "quarter" | "month" | "week";

export const ZOOM_LEVELS: ZoomLevel[] = ["year", "quarter", "month", "week"];

export const PIXELS_PER_DAY: Record<ZoomLevel, number> = {
  year: 3,
  quarter: 8,
  month: 20,
  week: 60,
};

export function dateToX(date: Date, rangeStart: Date, zoom: ZoomLevel): number {
  return daysBetween(rangeStart, date) * PIXELS_PER_DAY[zoom];
}

export function timelineWidth(rangeStart: Date, rangeEnd: Date, zoom: ZoomLevel): number {
  return dateToX(addDays(rangeEnd, 1), rangeStart, zoom);
}

function mondayOnOrBefore(date: Date): Date {
  const result = new Date(date);
  const dow = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - dow);
  return result;
}

export interface HeaderBlock {
  key: string;
  label: string;
  x: number;
  width: number;
}

export interface WeekHeaderBlock extends HeaderBlock {
  isoYear: number;
  isoWeek: number;
}

/** Month (or quarter/year, depending on zoom) header blocks spanning the visible range. */
export function monthBlocks(rangeStart: Date, rangeEnd: Date, zoom: ZoomLevel): HeaderBlock[] {
  const blocks: HeaderBlock[] = [];
  let cursor = new Date(rangeStart.getFullYear(), rangeStart.getMonth(), 1);
  while (cursor <= rangeEnd) {
    const nextMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    const blockStart = cursor < rangeStart ? rangeStart : cursor;
    const blockEnd = nextMonth < rangeEnd ? nextMonth : addDays(rangeEnd, 1);
    const x = dateToX(blockStart, rangeStart, zoom);
    const width = dateToX(blockEnd, rangeStart, zoom) - x;
    blocks.push({
      key: `${cursor.getFullYear()}-${cursor.getMonth()}`,
      label: cursor.toLocaleDateString("en-GB", { month: "short", year: "numeric" }),
      x,
      width,
    });
    cursor = nextMonth;
  }
  return blocks;
}

/** ISO week header blocks. Only meaningful at "week"/"month" zoom — too dense otherwise. */
export function weekBlocks(rangeStart: Date, rangeEnd: Date, zoom: ZoomLevel): WeekHeaderBlock[] {
  const blocks: WeekHeaderBlock[] = [];
  let cursor = mondayOnOrBefore(rangeStart);
  while (cursor <= rangeEnd) {
    const nextWeek = addDays(cursor, 7);
    const blockStart = cursor < rangeStart ? rangeStart : cursor;
    const blockEnd = nextWeek < rangeEnd ? nextWeek : addDays(rangeEnd, 1);
    const x = dateToX(blockStart, rangeStart, zoom);
    const width = dateToX(blockEnd, rangeStart, zoom) - x;
    const { isoYear, week } = getISOWeek(blockStart);
    blocks.push({ key: `${isoYear}-W${week}`, label: `W${week}`, x, width, isoYear, isoWeek: week });
    cursor = nextWeek;
  }
  return blocks;
}
