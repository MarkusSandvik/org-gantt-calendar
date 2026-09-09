import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Team, TeamCreatePayload, TeamUpdatePayload } from "../../api/types";
import { useToast } from "../../components/Toast";
import { useProject } from "../../contexts/ProjectContext";
import { usePermissions } from "../../hooks/usePermissions";
import { TeamFormModal } from "./TeamFormModal";

const CATEGORY_LABELS: Record<Team["category"], string> = {
  hardware: "Hardware",
  software: "Software",
  organization: "Organization",
};

export function TeamsAdmin() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { canManageTeams } = usePermissions();

  const { project, canEdit } = useProject();
  const projectId = project?.id;

  const { data: teams, isLoading } = useQuery({
    queryKey: ["teams", { projectId }],
    queryFn: () => api.get<Team[]>(`/teams?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const [expandedTeamId, setExpandedTeamId] = useState<number | null>(null);
  const [modalTeam, setModalTeam] = useState<Team | null | undefined>(undefined);
  const [formError, setFormError] = useState<string | null>(null);

  function closeModal() {
    setModalTeam(undefined);
    setFormError(null);
  }

  const createMutation = useMutation({
    mutationFn: (payload: TeamCreatePayload) => api.post<Team>("/teams", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      closeModal();
      showToast("Team created");
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: TeamUpdatePayload }) =>
      api.patch<Team>(`/teams/${id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      closeModal();
      showToast("Team updated");
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/teams/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      closeModal();
      setExpandedTeamId(null);
      showToast("Team deleted");
    },
    onError: (err: ApiError) => showToast(err.message, "error"),
  });

  if (!projectId || isLoading) {
    return <p>Loading teams...</p>;
  }

  const expandedTeam = teams?.find((t) => t.id === expandedTeamId) ?? null;

  return (
    <div>
      <div className="toolbar">
        <p className="page__phase-note">
          Every active team, its category, and who leads and staffs it. Click a row to see its
          members.
        </p>
        {canManageTeams && canEdit && (
          <button className="button button--primary" onClick={() => setModalTeam(null)}>
            New Team
          </button>
        )}
      </div>

      {teams && teams.length === 0 && <p>No teams yet.</p>}

      {teams && teams.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Lead</th>
              <th>Members</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {teams.map((team) => {
              const lead = team.members.find((m) => m.team_role === "lead");
              return (
                <tr
                  key={team.id}
                  onClick={() => setExpandedTeamId(team.id === expandedTeamId ? null : team.id)}
                  className={team.id === expandedTeamId ? "data-table__row--selected" : ""}
                >
                  <td>{team.name}</td>
                  <td>{CATEGORY_LABELS[team.category]}</td>
                  <td>{lead?.name ?? "—"}</td>
                  <td>{team.members.length}</td>
                  <td>
                    {canManageTeams && canEdit && (
                      <button
                        className="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setModalTeam(team);
                        }}
                      >
                        Edit
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {expandedTeam && (
        <div className="team-members">
          <h2>{expandedTeam.name} — members</h2>
          {expandedTeam.members.length === 0 && (
            <p>No one is assigned to this team yet. Add members from Admin &gt; Users.</p>
          )}
          {expandedTeam.members.length > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {expandedTeam.members.map((member) => (
                  <tr key={member.id}>
                    <td>{member.name}</td>
                    <td>{member.email}</td>
                    <td>{member.team_role === "lead" ? "Lead" : "Member"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {modalTeam !== undefined && (
        <TeamFormModal
          projectId={projectId}
          team={modalTeam}
          submitting={createMutation.isPending || updateMutation.isPending}
          errorMessage={formError}
          onClose={closeModal}
          onSubmit={(payload) => {
            setFormError(null);
            if (modalTeam) {
              updateMutation.mutate({ id: modalTeam.id, payload: payload as TeamUpdatePayload });
            } else {
              createMutation.mutate(payload as TeamCreatePayload);
            }
          }}
          onDelete={
            modalTeam && canEdit
              ? () => {
                  if (confirm(`Delete team "${modalTeam.name}"? This cannot be undone.`)) {
                    deleteMutation.mutate(modalTeam.id);
                  }
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
