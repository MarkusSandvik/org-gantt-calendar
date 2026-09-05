import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type {
  Dependency,
  Milestone,
  MilestoneStatus,
  MilestoneWritePayload,
  Project,
  Tag,
  Team,
  User,
} from "../../api/types";
import { MilestoneStatusBadge } from "../../components/MilestoneStatusBadge";
import { usePermissions } from "../../hooks/usePermissions";
import { MilestoneFormModal } from "./MilestoneFormModal";

const STATUS_FILTER_OPTIONS: MilestoneStatus[] = [
  "not_started",
  "on_track",
  "at_risk",
  "completed",
  "missed",
];

export function MilestonesPage() {
  const queryClient = useQueryClient();
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

  const [teamFilter, setTeamFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const { data: milestones, isLoading } = useQuery({
    queryKey: ["milestones", "filtered", { projectId, teamFilter, statusFilter, search }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (projectId) params.set("project_id", String(projectId));
      if (teamFilter) params.set("team_id", teamFilter);
      if (statusFilter) params.set("status", statusFilter);
      if (search) params.set("q", search);
      return api.get<Milestone[]>(`/milestones?${params.toString()}`);
    },
    enabled: projectId != null,
  });

  const [modalMilestone, setModalMilestone] = useState<Milestone | null | undefined>(undefined);
  const [formError, setFormError] = useState<string | null>(null);

  function closeModal() {
    setModalMilestone(undefined);
    setFormError(null);
  }

  const createMutation = useMutation({
    mutationFn: (payload: MilestoneWritePayload) =>
      api.post<Milestone>("/milestones", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["milestones"] });
      closeModal();
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: MilestoneWritePayload }) =>
      api.patch<Milestone>(`/milestones/${id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["milestones"] });
      closeModal();
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/milestones/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["milestones"] });
      closeModal();
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  if (!projectId) {
    return <p>Loading project...</p>;
  }

  return (
    <div className="page">
      <h1>Milestones</h1>

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
          <input
            className="filter-bar__search"
            placeholder="Search title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {canCreateAnywhere && (
          <button className="button button--primary" onClick={() => setModalMilestone(null)}>
            New Milestone
          </button>
        )}
      </div>

      {isLoading && <p>Loading milestones...</p>}
      {milestones && milestones.length === 0 && <p>No milestones match these filters.</p>}

      {milestones && milestones.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Date</th>
              <th>Team</th>
              <th>Owner</th>
              <th>Status</th>
              <th>Tags</th>
            </tr>
          </thead>
          <tbody>
            {milestones.map((milestone) => (
              <tr key={milestone.id} onClick={() => setModalMilestone(milestone)}>
                <td>{milestone.title}</td>
                <td>{milestone.date}</td>
                <td>{milestone.team?.name ?? "—"}</td>
                <td>{milestone.owner_user?.name ?? "—"}</td>
                <td>
                  <MilestoneStatusBadge status={milestone.status} />
                </td>
                <td>
                  {milestone.tags.map((t) => (
                    <span key={t.id} className="tag-chip">
                      {t.name}
                    </span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {modalMilestone !== undefined && teams && users && tags && (
        <MilestoneFormModal
          projectId={projectId}
          milestone={modalMilestone}
          teams={teams}
          users={users}
          tags={tags}
          hasDependencies={
            modalMilestone != null &&
            (dependencies ?? []).some(
              (d) =>
                (d.predecessor_type === "milestone" && d.predecessor_id === modalMilestone.id) ||
                (d.successor_type === "milestone" && d.successor_id === modalMilestone.id),
            )
          }
          submitting={createMutation.isPending || updateMutation.isPending}
          errorMessage={formError}
          onClose={closeModal}
          onSubmit={(payload) => {
            setFormError(null);
            if (modalMilestone) {
              updateMutation.mutate({ id: modalMilestone.id, payload });
            } else {
              createMutation.mutate(payload);
            }
          }}
          onDelete={
            modalMilestone
              ? () => {
                  if (confirm(`Delete "${modalMilestone.title}"? This cannot be undone.`)) {
                    deleteMutation.mutate(modalMilestone.id);
                  }
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
