import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
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
import { MonthGrid } from "../../components/calendar/MonthGrid";
import { buildMonthGrid } from "../../components/calendar/monthLayout";
import { addDays, formatISODate } from "../../utils/date";

const MONTH_LABEL = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric" });

export function CalendarMonthPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());

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

  const grid = useMemo(() => buildMonthGrid(year, month), [year, month]);
  const rangeStart = grid[0].days[0].date;
  const rangeEnd = addDays(grid[grid.length - 1].days[6].date, 1);

  const { data: events } = useQuery({
    queryKey: ["calendar-events", { projectId, from: formatISODate(rangeStart), to: formatISODate(rangeEnd) }],
    queryFn: () =>
      api.get<CalendarEvent[]>(
        `/calendar-events?project_id=${projectId}&date_from=${formatISODate(rangeStart)}T00:00:00&date_to=${formatISODate(rangeEnd)}T00:00:00`,
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

  function goToMonth(delta: number) {
    const next = new Date(year, month + delta, 1);
    setYear(next.getFullYear());
    setMonth(next.getMonth());
  }

  if (!projectId) {
    return <p>Loading calendar...</p>;
  }

  return (
    <div className="page">
      <h1>Calendar</h1>

      <div className="calendar-toolbar">
        <div className="calendar-toolbar__nav">
          <button type="button" className="button" onClick={() => goToMonth(-1)}>
            ← Prev
          </button>
          <button
            type="button"
            className="button"
            onClick={() => {
              setYear(today.getFullYear());
              setMonth(today.getMonth());
            }}
          >
            Today
          </button>
          <button type="button" className="button" onClick={() => goToMonth(1)}>
            Next →
          </button>
        </div>
        <h2 className="calendar-toolbar__label">{MONTH_LABEL.format(new Date(year, month, 1))}</h2>
        <button
          type="button"
          className="button button--primary"
          onClick={() => setModalState({ event: null, defaultDate: today })}
        >
          New Event
        </button>
      </div>

      <MonthGrid
        year={year}
        month={month}
        events={events ?? []}
        onDayClick={(date) => setModalState({ event: null, defaultDate: date })}
        onEventClick={(event) => setModalState({ event, defaultDate: null })}
        onWeekClick={(isoYear, isoWeek) => navigate(`/calendar/week/${isoYear}/${isoWeek}`)}
      />

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
