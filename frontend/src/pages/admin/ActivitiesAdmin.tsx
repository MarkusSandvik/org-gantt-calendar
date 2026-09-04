import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, ApiError } from "../../api/client";
import type {
  Activity,
  ActivityStatus,
  ActivityWritePayload,
  Priority,
  Project,
  Tag,
  Team,
  User,
} from "../../api/types";
import { PriorityBadge } from "../../components/PriorityBadge";
import { StatusBadge } from "../../components/StatusBadge";
import { ActivityFormModal } from "./ActivityFormModal";

const STATUS_FILTER_OPTIONS: ActivityStatus[] = [
  "not_started",
  "in_progress",
  "completed",
  "delayed",
  "blocked",
];

const PRIORITY_FILTER_OPTIONS: Priority[] = ["low", "normal", "high", "critical"];

export function ActivitiesAdmin() {
  const queryClient = useQueryClient();

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

  const [teamFilter, setTeamFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [search, setSearch] = useState("");

  const activitiesQueryKey = useMemo(
    () => ["activities", { projectId, teamFilter, statusFilter, priorityFilter, search }],
    [projectId, teamFilter, statusFilter, priorityFilter, search],
  );

  const { data: activities, isLoading } = useQuery({
    queryKey: activitiesQueryKey,
    queryFn: () => {
      const params = new URLSearchParams();
      if (projectId) params.set("project_id", String(projectId));
      if (teamFilter) params.set("team_id", teamFilter);
      if (statusFilter) params.set("status", statusFilter);
      if (priorityFilter) params.set("priority", priorityFilter);
      if (search) params.set("q", search);
      return api.get<Activity[]>(`/activities?${params.toString()}`);
    },
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
        <div className="filter-bar">
          <select value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)}>
            <option value="">All teams</option>
            {teams?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {STATUS_FILTER_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </select>
          <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
            <option value="">All priorities</option>
            {PRIORITY_FILTER_OPTIONS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <input
            placeholder="Search title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button className="button button--primary" onClick={() => setModalActivity(null)}>
          New Activity
        </button>
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
