import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Activity, CalendarEvent, Milestone, Project } from "../api/types";
import { MilestoneStatusBadge } from "../components/MilestoneStatusBadge";
import { PriorityBadge } from "../components/PriorityBadge";
import { StatusBadge } from "../components/StatusBadge";
import { useCurrentUser } from "../hooks/useAuth";
import { formatISODate } from "../utils/date";

const EVENT_DATETIME_FORMAT = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

function mergeById(...lists: Activity[][]): Activity[] {
  const byId = new Map<number, Activity>();
  for (const list of lists) {
    for (const activity of list) byId.set(activity.id, activity);
  }
  return Array.from(byId.values()).sort((a, b) => a.end_date.localeCompare(b.end_date));
}

export function MyTasks() {
  const navigate = useNavigate();
  const { me } = useCurrentUser();
  const userId = me?.id;

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const projectId = projects?.[0]?.id;

  const { data: ownedActivities } = useQuery({
    queryKey: ["activities", "my-tasks-owned", projectId, userId],
    queryFn: () =>
      api.get<Activity[]>(`/activities?project_id=${projectId}&owner_user_id=${userId}`),
    enabled: projectId != null && userId != null,
  });
  const { data: contributedActivities } = useQuery({
    queryKey: ["activities", "my-tasks-contributed", projectId, userId],
    queryFn: () =>
      api.get<Activity[]>(`/activities?project_id=${projectId}&contributor_user_id=${userId}`),
    enabled: projectId != null && userId != null,
  });
  const myActivities = mergeById(ownedActivities ?? [], contributedActivities ?? []);

  const { data: milestonesRaw } = useQuery({
    queryKey: ["milestones", "my-tasks", projectId, userId],
    queryFn: () =>
      api.get<Milestone[]>(`/milestones?project_id=${projectId}&owner_user_id=${userId}`),
    enabled: projectId != null && userId != null,
  });
  const myMilestones = (milestonesRaw ?? [])
    .filter((m) => m.status !== "completed" && m.status !== "missed")
    .sort((a, b) => a.date.localeCompare(b.date));

  const today = formatISODate(new Date());
  const { data: eventsRaw } = useQuery({
    queryKey: ["calendar-events", "my-tasks", projectId, userId, today],
    queryFn: () =>
      api.get<CalendarEvent[]>(
        `/calendar-events?project_id=${projectId}&owner_user_id=${userId}&date_from=${today}T00:00:00`,
      ),
    enabled: projectId != null && userId != null,
  });
  const myEvents = [...(eventsRaw ?? [])].sort((a, b) =>
    a.start_datetime.localeCompare(b.start_datetime),
  );

  if (!userId) {
    return <p>Loading...</p>;
  }

  return (
    <div className="page">
      <h1>My Tasks</h1>
      <p className="page__phase-note">
        Activities, milestones, and upcoming events for {me?.name ?? "this user"}.
      </p>

      <section className="dashboard-section">
        <h2>My Activities</h2>
        {myActivities.length === 0 && <p>No activities assigned to you.</p>}
        {myActivities.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Team</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Progress</th>
                <th>Dates</th>
              </tr>
            </thead>
            <tbody>
              {myActivities.map((activity) => (
                <tr
                  key={activity.id}
                  onClick={() =>
                    navigate(`/admin/activities?q=${encodeURIComponent(activity.title)}`)
                  }
                >
                  <td>{activity.title}</td>
                  <td>{activity.owner_team?.name ?? "—"}</td>
                  <td>
                    <StatusBadge status={activity.status} />
                  </td>
                  <td>
                    <PriorityBadge priority={activity.priority} />
                  </td>
                  <td>{activity.progress_percent}%</td>
                  <td>
                    {activity.start_date} → {activity.end_date}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="dashboard-section">
        <h2>My Milestones</h2>
        {myMilestones.length === 0 && <p>No outstanding milestones.</p>}
        {myMilestones.length > 0 && (
          <ul className="dashboard-list">
            {myMilestones.map((m) => (
              <li key={m.id}>
                <span className="dashboard-list__title">{m.title}</span>
                <MilestoneStatusBadge status={m.status} />
                <span className="dashboard-list__meta">
                  {m.team ? `${m.team.name} · ` : ""}
                  {m.date}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="dashboard-section">
        <h2>My Upcoming Events</h2>
        {myEvents.length === 0 && <p>No upcoming events.</p>}
        {myEvents.length > 0 && (
          <ul className="dashboard-list">
            {myEvents.map((event) => (
              <li key={event.id}>
                <span className="dashboard-list__title">{event.title}</span>
                <span className={`event-chip event-chip--${event.event_type}`}>
                  {event.event_type}
                </span>
                <span className="dashboard-list__meta">
                  {EVENT_DATETIME_FORMAT.format(new Date(event.start_datetime))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
