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
import { CalendarEventModal } from "../../components/calendar/CalendarEventModal";
import { CalendarViewSwitcher } from "../../components/calendar/CalendarViewSwitcher";
import { buildMonthGrid } from "../../components/calendar/monthLayout";
import { formatISODate } from "../../utils/date";

const MONTH_NAMES = Array.from({ length: 12 }, (_, i) =>
  new Intl.DateTimeFormat("en-GB", { month: "long" }).format(new Date(2000, i, 1)),
);
const DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"];

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

export function CalendarYearPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const params = useParams<{ year?: string }>();
  const today = new Date();
  const [year, setYear] = useState(params.year ? Number(params.year) : today.getFullYear());
  const todayKey = formatISODate(today);

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
  const { data: activities } = useQuery({
    queryKey: ["activities", "all", { projectId }],
    queryFn: () => api.get<Activity[]>(`/activities?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const rangeFrom = `${year}-01-01`;
  const rangeTo = `${year}-12-31`;
  const { data: events } = useQuery({
    queryKey: ["calendar-events", { projectId, from: rangeFrom, to: rangeTo }],
    queryFn: () =>
      api.get<CalendarEvent[]>(
        `/calendar-events?project_id=${projectId}&date_from=${rangeFrom}T00:00:00&date_to=${rangeTo}T23:59:59`,
      ),
    enabled: projectId != null,
  });
  const grouped = useMemo(() => eventsByDay(events ?? []), [events]);

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

  if (!projectId) {
    return <p>Loading calendar...</p>;
  }

  return (
    <div className="page">
      <h1>Calendar</h1>

      <div className="calendar-toolbar">
        <div className="calendar-toolbar__nav">
          <button type="button" className="button" onClick={() => setYear((y) => y - 1)}>
            ← Prev
          </button>
          <button type="button" className="button" onClick={() => setYear(today.getFullYear())}>
            Today
          </button>
          <button type="button" className="button" onClick={() => setYear((y) => y + 1)}>
            Next →
          </button>
        </div>
        <h2 className="calendar-toolbar__label">{year}</h2>
        <CalendarViewSwitcher
          active="year"
          monthHref={`/calendar/month/${year}/${today.getFullYear() === year ? today.getMonth() + 1 : 1}`}
          weekHref={`/calendar/week/${year}/1`}
          yearHref={`/calendar/year/${year}`}
        />
        <button
          type="button"
          className="button button--primary"
          onClick={() => setModalState({ event: null, defaultDate: today })}
        >
          New Event
        </button>
      </div>

      <div className="year-grid">
        {MONTH_NAMES.map((name, monthIndex) => {
          const rows = buildMonthGrid(year, monthIndex);
          return (
            <div key={name} className="year-grid__month">
              <button
                type="button"
                className="year-grid__month-header"
                onClick={() => navigate(`/calendar/month/${year}/${monthIndex + 1}`)}
              >
                {name}
              </button>
              <div className="year-grid__day-labels">
                {DAY_LABELS.map((label, i) => (
                  <span key={i}>{label}</span>
                ))}
              </div>
              {rows.map((row) => (
                <div key={`${row.isoYear}-${row.isoWeek}`} className="year-grid__row">
                  {row.days.map((day) => {
                    const key = formatISODate(day.date);
                    const dayEvents = grouped.get(key) ?? [];
                    return (
                      <button
                        key={key}
                        type="button"
                        className={
                          "year-grid__day" +
                          (day.inCurrentMonth ? "" : " year-grid__day--outside") +
                          (dayEvents.length > 0 ? " year-grid__day--has-events" : "") +
                          (key === todayKey ? " year-grid__day--today" : "")
                        }
                        title={dayEvents.map((e) => e.title).join(", ") || undefined}
                        onClick={() => navigate(`/calendar/month/${year}/${monthIndex + 1}`)}
                      >
                        {day.date.getDate()}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {modalState && teams && users && activities && (
        <CalendarEventModal
          projectId={projectId}
          event={modalState.event}
          defaultDate={modalState.defaultDate}
          teams={teams}
          users={users}
          activities={activities}
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
