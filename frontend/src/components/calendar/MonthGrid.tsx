import type { CalendarEvent } from "../../api/types";
import { formatISODate } from "../../utils/date";
import { buildMonthGrid } from "./monthLayout";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface MonthGridProps {
  year: number;
  month: number;
  events: CalendarEvent[];
  onDayClick: (date: Date) => void;
  onEventClick: (event: CalendarEvent) => void;
  onWeekClick: (isoYear: number, isoWeek: number) => void;
}

function eventsByDay(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
  const map = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const day = event.start_datetime.slice(0, 10);
    const list = map.get(day) ?? [];
    list.push(event);
    map.set(day, list);
  }
  return map;
}

export function MonthGrid({
  year,
  month,
  events,
  onDayClick,
  onEventClick,
  onWeekClick,
}: MonthGridProps) {
  const rows = buildMonthGrid(year, month);
  const grouped = eventsByDay(events);
  const today = new Date();
  const todayKey = formatISODate(today);

  return (
    <div className="month-grid">
      <div className="month-grid__row month-grid__row--header">
        <div className="month-grid__week-gutter" />
        {DAY_LABELS.map((label) => (
          <div key={label} className="month-grid__day-label">
            {label}
          </div>
        ))}
      </div>
      {rows.map((row) => (
        <div key={`${row.isoYear}-${row.isoWeek}`} className="month-grid__row">
          <button
            type="button"
            className="month-grid__week-gutter month-grid__week-link"
            onClick={() => onWeekClick(row.isoYear, row.isoWeek)}
            title={`Open week ${row.isoWeek}`}
          >
            W{row.isoWeek}
          </button>
          {row.days.map((day) => {
            const key = formatISODate(day.date);
            const dayEvents = grouped.get(key) ?? [];
            return (
              <div
                key={key}
                className={
                  "month-grid__day" +
                  (day.inCurrentMonth ? "" : " month-grid__day--outside") +
                  (key === todayKey ? " month-grid__day--today" : "")
                }
                onClick={() => onDayClick(day.date)}
              >
                <span className="month-grid__day-number">{day.date.getDate()}</span>
                <div className="month-grid__events">
                  {dayEvents.map((event) => (
                    <button
                      key={event.id}
                      type="button"
                      className={`event-chip event-chip--${event.event_type}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onEventClick(event);
                      }}
                      title={event.title}
                    >
                      {event.title}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
