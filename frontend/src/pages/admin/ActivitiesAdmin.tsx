import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type {
  Activity,
  ActivityWritePayload,
  Dependency,
  Project,
  Tag,
  Team,
  User,
} from "../../api/types";
import { FilterBar } from "../../components/filters/FilterBar";
import { PriorityBadge } from "../../components/PriorityBadge";
import { StatusBadge } from "../../components/StatusBadge";
import { useActivityFilters } from "../../hooks/useActivityFilters";
import { usePermissions } from "../../hooks/usePermissions";
import { ActivityFormModal } from "./ActivityFormModal";

export function ActivitiesAdmin() {
  const queryClient = useQueryClient();
  const { filters, setFilter, reset, isActive, toQueryString } = useActivityFilters();
  const { isAdmin, isLeadOfAnyTeam } = usePermissions();
  const canCreateAnywhere = isAdmin || isLeadOfAnyTeam;

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
  const { data: tags } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.get<Tag[]>("/tags"),
  });
  const { data: dependencies } = useQuery({
    queryKey: ["dependencies"],
    queryFn: () => api.get<Dependency[]>("/dependencies"),
  });

  const filterQuery = toQueryString({ project_id: projectId });
  const { data: activities, isLoading } = useQuery({
    queryKey: ["activities", "filtered", filterQuery],
    queryFn: () => api.get<Activity[]>(`/activities?${filterQuery}`),
    enabled: projectId != null,
  });

  const [modalActivity, setModalActivity] = useState<Activity | null | undefined>(undefined);
  const [formError, setFormError] = useState<string | null>(null);

  function closeModal() {
    setModalActivity(undefined);
    setFormError(null);
  }

  const createMutation = useMutation({
    mutationFn: (payload: ActivityWritePayload) => api.post<Activity>("/activities", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
      closeModal();
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ActivityWritePayload }) =>
      api.patch<Activity>(`/activities/${id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
      closeModal();
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/activities/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activities"] });
      closeModal();
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  if (!projectId) {
    return <p>Loading project...</p>;
  }

  return (
    <div>
      <div className="toolbar">
        <FilterBar
          filters={filters}
          onChange={setFilter}
          onReset={reset}
          isActive={isActive}
          teams={teams ?? []}
          users={users ?? []}
          tags={tags ?? []}
        />
        {canCreateAnywhere && (
          <button className="button button--primary" onClick={() => setModalActivity(null)}>
            New Activity
          </button>
        )}
      </div>

      {isLoading && <p>Loading activities...</p>}

      {activities && activities.length === 0 && <p>No activities match these filters.</p>}

      {activities && activities.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Team</th>
              <th>Owner</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Progress</th>
              <th>Dates</th>
            </tr>
          </thead>
          <tbody>
            {activities.map((activity) => (
              <tr key={activity.id} onClick={() => setModalActivity(activity)}>
                <td>{activity.title}</td>
                <td>{activity.owner_team?.name ?? "—"}</td>
                <td>{activity.owner_user?.name ?? "—"}</td>
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

      {modalActivity !== undefined && teams && users && tags && (
        <ActivityFormModal
          projectId={projectId}
          activity={modalActivity}
          teams={teams}
          users={users}
          tags={tags}
          hasDependencies={
            modalActivity != null &&
            (dependencies ?? []).some(
              (d) =>
                (d.predecessor_type === "activity" && d.predecessor_id === modalActivity.id) ||
                (d.successor_type === "activity" && d.successor_id === modalActivity.id),
            )
          }
          submitting={createMutation.isPending || updateMutation.isPending}
          errorMessage={formError}
          onClose={closeModal}
          onSubmit={(payload) => {
            setFormError(null);
            if (modalActivity) {
              updateMutation.mutate({ id: modalActivity.id, payload });
            } else {
              createMutation.mutate(payload);
            }
          }}
          onDelete={
            modalActivity
              ? () => {
                  if (confirm(`Delete "${modalActivity.title}"? This cannot be undone.`)) {
                    deleteMutation.mutate(modalActivity.id);
                  }
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
