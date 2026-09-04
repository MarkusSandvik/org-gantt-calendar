export type ZoomLevel = "year" | "quarter" | "month" | "week";

export const ZOOM_LEVELS: ZoomLevel[] = ["year", "quarter", "month", "week"];

export const PIXELS_PER_DAY: Record<ZoomLevel, number> = {
  year: 3,
  quarter: 8,
  month: 20,
  week: 60,
};

const MS_PER_DAY = 86_400_000;

export function parseISODate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function daysBetween(a: Date, b: Date): number {
  return Math.round((b.getTime() - a.getTime()) / MS_PER_DAY);
}

export function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

export function dateToX(date: Date, rangeStart: Date, zoom: ZoomLevel): number {
  return daysBetween(rangeStart, date) * PIXELS_PER_DAY[zoom];
}

export function timelineWidth(rangeStart: Date, rangeEnd: Date, zoom: ZoomLevel): number {
  return dateToX(addDays(rangeEnd, 1), rangeStart, zoom);
}

/** ISO 8601 week number (Monday-start weeks, week 1 contains the year's first Thursday). */
export function getISOWeek(date: Date): { isoYear: number; week: number } {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - dayNum + 3);
  const firstThursday = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  const firstDayNum = (firstThursday.getUTCDay() + 6) % 7;
  firstThursday.setUTCDate(firstThursday.getUTCDate() - firstDayNum + 3);
  const week = 1 + Math.round((d.getTime() - firstThursday.getTime()) / (7 * MS_PER_DAY));
  return { isoYear: d.getUTCFullYear(), week };
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
export function weekBlocks(rangeStart: Date, rangeEnd: Date, zoom: ZoomLevel): HeaderBlock[] {
  const blocks: HeaderBlock[] = [];
  let cursor = mondayOnOrBefore(rangeStart);
  while (cursor <= rangeEnd) {
    const nextWeek = addDays(cursor, 7);
    const blockStart = cursor < rangeStart ? rangeStart : cursor;
    const blockEnd = nextWeek < rangeEnd ? nextWeek : addDays(rangeEnd, 1);
    const x = dateToX(blockStart, rangeStart, zoom);
    const width = dateToX(blockEnd, rangeStart, zoom) - x;
    const { isoYear, week } = getISOWeek(blockStart);
    blocks.push({ key: `${isoYear}-W${week}`, label: `W${week}`, x, width });
    cursor = nextWeek;
  }
  return blocks;
}
