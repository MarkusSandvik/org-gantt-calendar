import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Activity, CalendarEvent, CalendarEventWritePayload, Tag, Team, User } from "../../api/types";
import { AnnualWheel } from "../../components/calendar/AnnualWheel";
import { CalendarEventModal } from "../../components/calendar/CalendarEventModal";
import { CalendarFilterBar } from "../../components/calendar/CalendarFilterBar";
import { CalendarViewSwitcher } from "../../components/calendar/CalendarViewSwitcher";
import { confirmDeleteCalendarEvent } from "../../components/calendar/confirmDeleteCalendarEvent";
import { useProject } from "../../contexts/ProjectContext";
import { ORGANIZATION_TEAM_FILTER, calendarQuerySuffix, useCalendarFilters } from "../../hooks/useCalendarFilters";
import { addDays, formatISODate } from "../../utils/date";

export function CalendarWheelPage() {
  const queryClient = useQueryClient();
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const { project, canEdit } = useProject();
  const projectId = project?.id;
  const projectSlug = project?.slug;

  const { data: teams } = useQuery({
    queryKey: ["teams", { projectId }],
    queryFn: () => api.get<Team[]>(`/teams?project_id=${projectId}`),
    enabled: projectId != null,
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
  const { data: tags } = useQuery({
    queryKey: ["tags", { projectId }],
    queryFn: () => api.get<Tag[]>(`/tags?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const { teamFilter, tagFilter, setTeamFilter, setTagFilter, queryParams } = useCalendarFilters(project);

  // The pie chart mirrors the same team scope as the Calendar's own filter
  // (Organization/a specific team/no filter) rather than always showing
  // every activity in the project — "Related activity" below deliberately
  // keeps using the unfiltered `activities` list, since picking one there
  // is a data-entry concern independent of what the wheel is displaying.
  const wheelActivities = (activities ?? []).filter((activity) => {
    if (!teamFilter) return true;
    if (teamFilter === ORGANIZATION_TEAM_FILTER) return activity.all_teams;
    return activity.owner_team?.id === Number(teamFilter);
  });

  // The wheel is a rolling 365-day window starting today, not a calendar
  // year — it re-centers on whatever "today" is whenever it's opened,
  // rather than showing Jan-Dec of a fixed year.
  const rangeFrom = formatISODate(today);
  const rangeTo = formatISODate(addDays(today, 364));
  const { data: events } = useQuery({
    queryKey: ["calendar-events", { projectId, from: rangeFrom, to: rangeTo, ...queryParams }],
    queryFn: () =>
      api.get<CalendarEvent[]>(
        `/calendar-events?project_id=${projectId}&date_from=${rangeFrom}T00:00:00&date_to=${rangeTo}T23:59:59${calendarQuerySuffix(queryParams)}`,
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
    mutationFn: ({ id, deleteFuture }: { id: number; deleteFuture: boolean }) =>
      api.delete(`/calendar-events/${id}${deleteFuture ? "?delete_future=true" : ""}`),
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
      <p className="page__phase-note">
        The annual wheel — today is always at the top, with the next 12 months laid out clockwise
        around it.
      </p>

      <div className="calendar-toolbar">
        <div className="calendar-toolbar__nav" />
        <div className="calendar-toolbar__label" />
        <CalendarViewSwitcher
          active="wheel"
          monthHref={`/${projectSlug}/calendar/month/${today.getFullYear()}/${today.getMonth() + 1}`}
          weekHref={`/${projectSlug}/calendar/week/${today.getFullYear()}/1`}
          yearHref={`/${projectSlug}/calendar/year/${today.getFullYear()}`}
          wheelHref={`/${projectSlug}/calendar/wheel`}
        />
        {canEdit && (
          <button
            type="button"
            className="button button--primary"
            onClick={() => setModalState({ event: null, defaultDate: today })}
          >
            New Event
          </button>
        )}
      </div>

      <CalendarFilterBar
        teams={teams ?? []}
        tags={tags ?? []}
        teamFilter={teamFilter}
        tagFilter={tagFilter}
        onTeamChange={setTeamFilter}
        onTagChange={setTagFilter}
      />

      <AnnualWheel
        today={today}
        events={events ?? []}
        activities={wheelActivities}
        teams={teams ?? []}
        onEventClick={(event) => setModalState({ event, defaultDate: null })}
      />

      {modalState && teams && users && activities && tags && (
        <CalendarEventModal
          projectId={projectId}
          event={modalState.event}
          defaultDate={modalState.defaultDate}
          teams={teams}
          users={users}
          activities={activities}
          tags={tags}
          canEditProject={canEdit}
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
            modalState.event && canEdit
              ? () => {
                  const scope = confirmDeleteCalendarEvent(modalState.event!);
                  if (scope) {
                    deleteMutation.mutate({
                      id: modalState.event!.id,
                      deleteFuture: scope === "series_future",
                    });
                  }
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
