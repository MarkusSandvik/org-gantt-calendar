import { addDays, daysBetween, getISOWeek } from "../../utils/date";

export interface CalendarDay {
  date: Date;
  inCurrentMonth: boolean;
}

export interface CalendarWeekRow {
  isoYear: number;
  isoWeek: number;
  days: CalendarDay[];
}

/** Full set of Monday-start week rows covering the given month, padded with
 * leading/trailing days from adjacent months so every row has 7 days. */
export function buildMonthGrid(year: number, month: number): CalendarWeekRow[] {
  const firstOfMonth = new Date(year, month, 1);
  const startOffset = (firstOfMonth.getDay() + 6) % 7;
  const gridStart = addDays(firstOfMonth, -startOffset);

  const lastOfMonth = new Date(year, month + 1, 0);
  const endOffset = 6 - ((lastOfMonth.getDay() + 6) % 7);
  const gridEnd = addDays(lastOfMonth, endOffset);

  const totalDays = daysBetween(gridStart, gridEnd) + 1;
  const rows: CalendarWeekRow[] = [];
  for (let i = 0; i < totalDays; i += 7) {
    const days: CalendarDay[] = [];
    for (let d = 0; d < 7; d++) {
      const date = addDays(gridStart, i + d);
      days.push({ date, inCurrentMonth: date.getMonth() === month });
    }
    const { isoYear, week } = getISOWeek(days[0].date);
    rows.push({ isoYear, isoWeek: week, days });
  }
  return rows;
}
