import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import type {
  Activity,
  CalendarEvent,
  CalendarEventWritePayload,
  Project,
  Team,
  User,
} from "../../api/types";
import { PriorityBadge } from "../../components/PriorityBadge";
import { StatusBadge } from "../../components/StatusBadge";
import { CalendarEventModal } from "../../components/calendar/CalendarEventModal";
import { addDays, formatISODate, getISOWeek, isoWeekToMonday } from "../../utils/date";

const DAY_FORMAT = new Intl.DateTimeFormat("en-GB", {
  weekday: "long",
  day: "numeric",
  month: "short",
});
const RANGE_FORMAT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" });

export function CalendarWeekPage() {
  const params = useParams<{ isoYear: string; isoWeek: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const isoYear = Number(params.isoYear);
  const isoWeek = Number(params.isoWeek);
  const monday = useMemo(() => isoWeekToMonday(isoYear, isoWeek), [isoYear, isoWeek]);
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(monday, i)), [monday]);
  const sunday = days[6];

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const projectId = projects?.[0]?.id;

  const { data: teams } = useQuery({
    queryKey: ["teams"],
    queryFn: () => api.get<Team[]>("/teams"),
  });
  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
  });
  const { data: allActivities } = useQuery({
    queryKey: ["activities", "all", { projectId }],
    queryFn: () => api.get<Activity[]>(`/activities?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const { data: events } = useQuery({
    queryKey: ["calendar-events", { projectId, from: formatISODate(monday), to: formatISODate(sunday) }],
    queryFn: () =>
      api.get<CalendarEvent[]>(
        `/calendar-events?project_id=${projectId}&date_from=${formatISODate(monday)}T00:00:00&date_to=${formatISODate(sunday)}T23:59:59`,
      ),
    enabled: projectId != null,
  });

  const { data: runningActivities } = useQuery({
    queryKey: ["activities", "week-running", { projectId, from: formatISODate(monday), to: formatISODate(sunday) }],
    queryFn: () =>
      api.get<Activity[]>(
        `/activities?project_id=${projectId}&date_from=${formatISODate(monday)}&date_to=${formatISODate(sunday)}`,
      ),
    enabled: projectId != null,
  });

  const [modalState, setModalState] = useState<
    { event: CalendarEvent | null; defaultDate: Date | null } | undefined
  >(undefined);
  const [formError, setFormError] = useState<string | null>(null);

  function closeModal() {
    setModalState(undefined);
    setFormError(null);
  }

  const createMutation = useMutation({
    mutationFn: (payload: CalendarEventWritePayload) =>
      api.post<CalendarEvent>("/calendar-events", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar-events"] });
      closeModal();
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: CalendarEventWritePayload }) =>
      api.patch<CalendarEvent>(`/calendar-events/${id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar-events"] });
      closeModal();
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/calendar-events/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar-events"] });
      closeModal();
    },
  });

  function goToWeek(deltaDays: number) {
    const newMonday = addDays(monday, deltaDays);
    const { isoYear: y, week } = getISOWeek(newMonday);
    navigate(`/calendar/week/${y}/${week}`);
  }

  function eventsForDay(day: Date): CalendarEvent[] {
    const key = formatISODate(day);
    return (events ?? []).filter((e) => e.start_datetime.slice(0, 10) === key);
  }

  if (!projectId) {
    return <p>Loading week...</p>;
  }

  return (
    <div className="page">
      <h1>
        Week {isoWeek} · {isoYear}
      </h1>
      <p className="page__phase-note">
        {RANGE_FORMAT.format(monday)} – {RANGE_FORMAT.format(sunday)}
      </p>

      <div className="calendar-toolbar">
        <div className="calendar-toolbar__nav">
          <button type="button" className="button" onClick={() => goToWeek(-7)}>
            ← Prev week
          </button>
          <button
            type="button"
            className="button"
            onClick={() => {
              const { isoYear: y, week } = getISOWeek(new Date());
              navigate(`/calendar/week/${y}/${week}`);
            }}
          >
            This week
          </button>
          <button type="button" className="button" onClick={() => goToWeek(7)}>
            Next week →
          </button>
        </div>
        <div className="calendar-toolbar__label" />
        <button
          type="button"
          className="button button--primary"
          onClick={() => setModalState({ event: null, defaultDate: monday })}
        >
          New Event
        </button>
      </div>

      <div className="week-view">
        <div className="week-view__days">
          {days.map((day) => (
            <div key={formatISODate(day)} className="week-view__day">
              <div className="week-view__day-header">{DAY_FORMAT.format(day)}</div>
              <div className="week-view__day-events">
                {eventsForDay(day).length === 0 && (
                  <p className="week-view__empty">No events</p>
                )}
                {eventsForDay(day).map((event) => (
                  <button
                    key={event.id}
                    type="button"
                    className={`event-chip event-chip--${event.event_type}`}
                    onClick={() => setModalState({ event, defaultDate: null })}
                  >
                    {event.all_day ? event.title : `${event.start_datetime.slice(11, 16)} ${event.title}`}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="week-view__running">
          <h2>Running project activities</h2>
          {runningActivities && runningActivities.length === 0 && (
            <p>No activities are running this week.</p>
          )}
          {runningActivities && runningActivities.length > 0 && (
            <ul className="week-view__running-list">
              {runningActivities.map((activity) => (
                <li key={activity.id}>
                  <span className="week-view__running-title">{activity.title}</span>
                  <StatusBadge status={activity.status} />
                  <PriorityBadge priority={activity.priority} />
                  <span className="week-view__running-progress">
                    {activity.progress_percent}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {modalState && teams && users && allActivities && (
        <CalendarEventModal
          projectId={projectId}
          event={modalState.event}
          defaultDate={modalState.defaultDate}
          teams={teams}
          users={users}
          activities={allActivities}
          submitting={createMutation.isPending || updateMutation.isPending}
          errorMessage={formError}
          onClose={closeModal}
          onSubmit={(payload) => {
            setFormError(null);
            if (modalState.event) {
              updateMutation.mutate({ id: modalState.event.id, payload });
            } else {
              createMutation.mutate(payload);
            }
          }}
          onDelete={
            modalState.event
              ? () => {
                  if (confirm(`Delete "${modalState.event!.title}"?`)) {
                    deleteMutation.mutate(modalState.event!.id);
                  }
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
