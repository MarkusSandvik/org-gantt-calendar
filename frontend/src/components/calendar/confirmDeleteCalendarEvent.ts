import type { CalendarEvent } from "../../api/types";

/** Shared by every Calendar page's delete flow. Returns null if the user
 * cancelled, "single" to delete just this occurrence, or "series_future"
 * to also delete every later occurrence in its recurring series (never
 * earlier ones — those already happened). */
export function confirmDeleteCalendarEvent(
  event: CalendarEvent,
): "single" | "series_future" | null {
  if (!confirm(`Delete "${event.title}"?`)) return null;
  if (event.recurrence_group_id == null) return "single";
  return confirm(
    "This event repeats. Also delete this and every future occurrence in the series?\n\n" +
      "OK = this and future occurrences. Cancel = just this one.",
  )
    ? "series_future"
    : "single";
}
