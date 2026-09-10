import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Project, Team } from "../../api/types";
import { projectLabel } from "../../components/ProjectStatusBadge";
import { useToast } from "../../components/Toast";

interface CopyMembersModalProps {
  targetProject: Project;
  sourceCandidates: Project[];
  onClose: () => void;
}

interface SelectionKey {
  targetTeamId: number;
  userId: number;
}

function keyOf(sel: SelectionKey): string {
  return `${sel.targetTeamId}:${sel.userId}`;
}

export function CopyMembersModal({
  targetProject,
  sourceCandidates,
  onClose,
}: CopyMembersModalProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [sourceId, setSourceId] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const sourceProjectId = sourceId ? Number(sourceId) : null;

  const { data: sourceTeams } = useQuery({
    queryKey: ["teams", { projectId: sourceProjectId }],
    queryFn: () => api.get<Team[]>(`/teams?project_id=${sourceProjectId}`),
    enabled: sourceProjectId != null,
  });
  const { data: targetTeams } = useQuery({
    queryKey: ["teams", { projectId: targetProject.id }],
    queryFn: () => api.get<Team[]>(`/teams?project_id=${targetProject.id}`),
  });

  // Only teams that (a) exist under the same name in both projects and (b)
  // don't already auto-transfer — those are handled automatically and
  // never need a manual choice here.
  const pairs = useMemo(() => {
    if (!sourceTeams || !targetTeams) return [];
    return targetTeams
      .filter((t) => !t.auto_transfer_membership)
      .map((targetTeam) => {
        const sourceTeam = sourceTeams.find(
          (s) => s.name.toLowerCase() === targetTeam.name.toLowerCase(),
        );
        return { targetTeam, sourceTeam };
      })
      .filter((p): p is { targetTeam: Team; sourceTeam: Team } => p.sourceTeam != null)
      .filter((p) => p.sourceTeam.members.length > 0);
  }, [sourceTeams, targetTeams]);

  const applyMutation = useMutation({
    mutationFn: async () => {
      const entries = Array.from(selected).map((k) => {
        const [targetTeamId, userId] = k.split(":").map(Number);
        return { targetTeamId, userId };
      });
      for (const entry of entries) {
        const pair = pairs.find((p) => p.targetTeam.id === entry.targetTeamId);
        const member = pair?.sourceTeam.members.find((m) => m.id === entry.userId);
        if (!pair || !member) continue;
        await api.put(`/users/${entry.userId}/team-memberships`, {
          team_id: entry.targetTeamId,
          team_role: member.team_role,
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      queryClient.invalidateQueries({ queryKey: ["users-admin"] });
      showToast("Members copied");
      onClose();
    },
    onError: (err: ApiError) => setError(err.message),
  });

  function toggle(sel: SelectionKey) {
    setSelected((prev) => {
      const next = new Set(prev);
      const k = keyOf(sel);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Copy Members into {projectLabel(targetProject)}</h2>
        <p className="page__phase-note">
          Board and Admin memberships already carry over automatically — pick who else moves
          into each team below. Nothing is selected by default.
        </p>

        <label>
          Copy from
          <select value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
            <option value="">Choose a project...</option>
            {sourceCandidates.map((p) => (
              <option key={p.id} value={p.id}>
                {projectLabel(p)}
              </option>
            ))}
          </select>
        </label>

        {sourceProjectId != null && pairs.length === 0 && (
          <p className="page__phase-note">
            No matching teams with members to copy from that project.
          </p>
        )}

        {pairs.map(({ targetTeam, sourceTeam }) => (
          <fieldset key={targetTeam.id}>
            <legend>{targetTeam.name}</legend>
            {sourceTeam.members.map((member) => (
              <label key={member.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selected.has(keyOf({ targetTeamId: targetTeam.id, userId: member.id }))}
                  onChange={() => toggle({ targetTeamId: targetTeam.id, userId: member.id })}
                />
                {member.name} ({member.team_role === "lead" ? "Lead" : "Member"})
              </label>
            ))}
          </fieldset>
        ))}

        {error && <p className="form-error">{error}</p>}

        <div className="modal-actions">
          <div className="modal-actions__spacer" />
          <button type="button" className="button" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="button button--primary"
            disabled={selected.size === 0 || applyMutation.isPending}
            onClick={() => {
              setError(null);
              applyMutation.mutate();
            }}
          >
            Copy {selected.size > 0 ? selected.size : ""} member{selected.size === 1 ? "" : "s"}
          </button>
        </div>
      </div>
    </div>
  );
}
