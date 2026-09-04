import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { CalendarEvent, DashboardSummary, Project } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";
import { addDays, formatISODate, parseISODate } from "../utils/date";

const WEEKDAY_FORMAT = new Intl.DateTimeFormat("en-GB", { weekday: "long" });
const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });

const METRIC_LABELS: { key: keyof DashboardSummary["week_counts"]; label: string }[] = [
  { key: "active_tasks", label: "active tasks" },
  { key: "milestones_this_week", label: "milestones" },
  { key: "delayed", label: "delayed" },
  { key: "blocked", label: "blocked" },
  { key: "social_activities", label: "social activities" },
  { key: "meetings", label: "meetings" },
  { key: "upcoming_deadlines", label: "upcoming deadline" },
];

export function Dashboard() {
  const navigate = useNavigate();

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const projectId = projects?.[0]?.id;

  const { data: summary } = useQuery({
    queryKey: ["dashboard-summary", projectId],
    queryFn: () => api.get<DashboardSummary>(`/dashboard/summary?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const { data: weekEvents } = useQuery({
    queryKey: ["calendar-events", "dashboard-week", summary?.week_start, summary?.week_end],
    queryFn: () =>
      api.get<CalendarEvent[]>(
        `/calendar-events?project_id=${projectId}&date_from=${summary!.week_start}T00:00:00&date_to=${summary!.week_end}T23:59:59`,
      ),
    enabled: projectId != null && summary != null,
  });

  if (!projectId || !summary) {
    return <p>Loading dashboard...</p>;
  }

  const activeMetrics = METRIC_LABELS.filter((m) => summary.week_counts[m.key] > 0);
  const weekdays = Array.from({ length: 5 }, (_, i) => addDays(parseISODate(summary.week_start), i));

  function eventsForDay(day: Date): CalendarEvent[] {
    const key = formatISODate(day);
    return (weekEvents ?? []).filter((e) => e.start_datetime.slice(0, 10) === key);
  }

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <p className="page__phase-note">
        Week {summary.iso_week} · {summary.week_start} – {summary.week_end}
      </p>

      {activeMetrics.length > 0 ? (
        <div className="dashboard-metrics">
          {activeMetrics.map((m) => (
            <div key={m.key} className="dashboard-metric">
              <span className="dashboard-metric__count">{summary.week_counts[m.key]}</span>
              <span className="dashboard-metric__label">{m.label}</span>
            </div>
          ))}
        </div>
      ) : (
        <p>Nothing notable this week.</p>
      )}

      <div className="dashboard-grid">
        <div className="dashboard-grid__left">
          <section className="dashboard-section">
            <h2>Upcoming Milestones</h2>
            {summary.upcoming_milestones.length === 0 && <p>No upcoming milestones.</p>}
            {summary.upcoming_milestones.length > 0 && (
              <ul className="dashboard-list">
                {summary.upcoming_milestones.map((m) => (
                  <li key={m.id}>
                    <span className="dashboard-list__title">{m.title}</span>
                    <span className="dashboard-list__meta">
                      {m.team ? `${m.team} · ` : ""}
                      {m.date}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="dashboard-section">
            <h2>Attention Required</h2>
            {summary.attention_required.length === 0 && <p>Nothing needs attention.</p>}
            {summary.attention_required.length > 0 && (
              <ul className="dashboard-list">
                {summary.attention_required.map((item) => (
                  <li
                    key={item.id}
                    className="dashboard-list__clickable"
                    onClick={() =>
                      navigate(`/admin/activities?q=${encodeURIComponent(item.title)}`)
                    }
                  >
                    <span className="dashboard-list__title">{item.title}</span>
                    <StatusBadge status={item.status} />
                    <span className="dashboard-list__meta">{item.detail}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <section className="dashboard-section dashboard-section--schedule">
          <h2>This Week's Schedule</h2>
          {weekdays.map((day) => {
            const dayEvents = eventsForDay(day);
            return (
              <div key={formatISODate(day)} className="dashboard-schedule-day">
                <div className="dashboard-schedule-day__header">
                  {WEEKDAY_FORMAT.format(day)} <span>{DATE_FORMAT.format(day)}</span>
                </div>
                <div className="dashboard-schedule-day__events">
                  {dayEvents.length === 0 && <p className="week-view__empty">No events</p>}
                  {dayEvents.map((event) => (
                    <span
                      key={event.id}
                      className={`event-chip event-chip--${event.event_type}`}
                      title={event.title}
                    >
                      {event.title}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}
