import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Project, ProjectUpdatePayload, Tag, Team } from "../../api/types";
import { useToast } from "../../components/Toast";
import { useProject } from "../../contexts/ProjectContext";
import { usePermissions } from "../../hooks/usePermissions";

interface FormState {
  default_gantt_team_id: string;
  default_gantt_tag_id: string;
  default_calendar_team_id: string;
  default_calendar_tag_id: string;
}

function toFormState(project: Project): FormState {
  return {
    default_gantt_team_id: project.default_gantt_team_id?.toString() ?? "",
    default_gantt_tag_id: project.default_gantt_tag_id?.toString() ?? "",
    default_calendar_team_id: project.default_calendar_all_teams
      ? "__organization__"
      : (project.default_calendar_team_id?.toString() ?? ""),
    default_calendar_tag_id: project.default_calendar_tag_id?.toString() ?? "",
  };
}

export function SettingsAdmin() {
  const { project } = useProject();
  const { isAdmin } = usePermissions();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: teams } = useQuery({
    queryKey: ["teams", { projectId: project?.id }],
    queryFn: () => api.get<Team[]>(`/teams?project_id=${project?.id}`),
    enabled: project != null,
  });
  const { data: tags } = useQuery({
    queryKey: ["tags", { projectId: project?.id }],
    queryFn: () => api.get<Tag[]>(`/tags?project_id=${project?.id}`),
    enabled: project != null,
  });

  const [form, setForm] = useState<FormState | null>(null);

  useEffect(() => {
    if (project) setForm(toFormState(project));
  }, [project?.id]);

  const updateMutation = useMutation({
    mutationFn: (payload: ProjectUpdatePayload) => api.patch<Project>(`/projects/${project!.id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      showToast("Default view settings saved");
    },
    onError: (err: ApiError) => showToast(err.message, "error"),
  });

  if (!project || !form) {
    return <p>Loading settings...</p>;
  }

  if (!isAdmin) {
    return <p>Only an Admin can change default view settings.</p>;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    updateMutation.mutate({
      default_gantt_team_id: form.default_gantt_team_id ? Number(form.default_gantt_team_id) : null,
      default_gantt_tag_id: form.default_gantt_tag_id ? Number(form.default_gantt_tag_id) : null,
      default_calendar_all_teams: form.default_calendar_team_id === "__organization__",
      default_calendar_team_id:
        form.default_calendar_team_id && form.default_calendar_team_id !== "__organization__"
          ? Number(form.default_calendar_team_id)
          : null,
      default_calendar_tag_id: form.default_calendar_tag_id ? Number(form.default_calendar_tag_id) : null,
    });
  }

  return (
    <div>
      <p className="page__phase-note">
        The starting team/tag filter each viewer sees when they open the Gantt or Calendar for "
        {project.name}" — anyone can still change their own filter afterward, this only sets what
        they see first.
      </p>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <legend>Project Schedule (Gantt) default view</legend>
          <div className="form-row">
            <label>
              Team
              <select
                value={form.default_gantt_team_id}
                onChange={(e) => setForm((f) => f && { ...f, default_gantt_team_id: e.target.value })}
              >
                <option value="">No default (all teams)</option>
                {(teams ?? []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tag
              <select
                value={form.default_gantt_tag_id}
                onChange={(e) => setForm((f) => f && { ...f, default_gantt_tag_id: e.target.value })}
              >
                <option value="">No default (all tags)</option>
                {(tags ?? []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </fieldset>

        <fieldset>
          <legend>Calendar default view</legend>
          <div className="form-row">
            <label>
              Team
              <select
                value={form.default_calendar_team_id}
                onChange={(e) =>
                  setForm((f) => f && { ...f, default_calendar_team_id: e.target.value })
                }
              >
                <option value="">No default (all teams)</option>
                <option value="__organization__">Organization</option>
                {(teams ?? []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tag
              <select
                value={form.default_calendar_tag_id}
                onChange={(e) =>
                  setForm((f) => f && { ...f, default_calendar_tag_id: e.target.value })
                }
              >
                <option value="">No default (all tags)</option>
                {(tags ?? []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </fieldset>

        <div className="modal-actions">
          <button type="submit" className="button button--primary" disabled={updateMutation.isPending}>
            Save
          </button>
        </div>
      </form>
    </div>
  );
}
