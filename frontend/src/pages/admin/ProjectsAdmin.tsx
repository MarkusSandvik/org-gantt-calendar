import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type {
  Project,
  ProjectCreatePayload,
  ProjectStatus,
  ProjectUpdatePayload,
} from "../../api/types";
import { ProjectStatusBadge, projectLabel } from "../../components/ProjectStatusBadge";
import { useToast } from "../../components/Toast";
import { usePermissions } from "../../hooks/usePermissions";
import { CopyMembersModal } from "./CopyMembersModal";
import { ProjectFormModal } from "./ProjectFormModal";

const NEXT_STATUS_ACTIONS: Record<ProjectStatus, { status: ProjectStatus; label: string }[]> = {
  draft: [
    { status: "active", label: "Activate" },
    { status: "archived", label: "Archive" },
  ],
  active: [
    { status: "completed", label: "Complete" },
    { status: "archived", label: "Archive" },
  ],
  completed: [
    { status: "active", label: "Reactivate" },
    { status: "archived", label: "Archive" },
  ],
  archived: [],
};

const CONFIRM_MESSAGES: Record<ProjectStatus, (project: Project) => string> = {
  active: (p) =>
    `Activate "${projectLabel(p)}"? It becomes the default project everyone lands on. Any other active project stays active and editable — mark it Completed separately once its work is actually done.`,
  completed: (p) => `Mark "${projectLabel(p)}" as Completed?`,
  archived: (p) =>
    `Archive "${projectLabel(p)}"? This is permanent — an archived project can never be reactivated, and becomes fully read-only.`,
  draft: () => "",
};

function formatDate(iso: string | null): string {
  return iso ?? "—";
}

// Archiving unconditionally clears is_default with nothing to pick a
// replacement, so the backend rejects archiving the current default —
// mirror that here rather than offering a button that would just 422.
function actionsFor(project: Project): { status: ProjectStatus; label: string }[] {
  const actions = NEXT_STATUS_ACTIONS[project.status];
  if (!project.is_default) return actions;
  return actions.filter((a) => a.status !== "archived");
}

// Mirrors the backend's own editable-statuses rule (services/projects.py::
// ensure_project_editable) — a completed/archived project's own record is
// frozen too, so there's no point offering an Edit button that would 422.
const EDITABLE_STATUSES: ProjectStatus[] = ["draft", "active"];

export function ProjectsAdmin() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { isAdmin } = usePermissions();

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });

  const [modalProject, setModalProject] = useState<Project | null | undefined>(undefined);
  const [copyMembersProject, setCopyMembersProject] = useState<Project | undefined>(undefined);
  const [formError, setFormError] = useState<string | null>(null);

  function closeModal() {
    setModalProject(undefined);
    setFormError(null);
  }

  const createMutation = useMutation({
    mutationFn: (payload: ProjectCreatePayload) => api.post<Project>("/projects", payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      closeModal();
      showToast(`"${projectLabel(created)}" created`);
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProjectUpdatePayload }) =>
      api.patch<Project>(`/projects/${id}`, payload),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      closeModal();
      showToast(`"${projectLabel(updated)}" updated`);
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ProjectStatus }) =>
      api.patch<Project>(`/projects/${id}/status`, { status }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      showToast(`"${projectLabel(updated)}" is now ${updated.status}`);
    },
    onError: (err: ApiError) => showToast(err.message, "error"),
  });

  if (isLoading) {
    return <p>Loading projects...</p>;
  }

  const sorted = [...(projects ?? [])].sort((a, b) => b.id - a.id);

  return (
    <div>
      <div className="toolbar">
        <p className="page__phase-note">
          Every project this organization has ever run — past seasons included. Only Admins can
          create projects or change their status.
        </p>
        {isAdmin && (
          <button className="button button--primary" onClick={() => setModalProject(null)}>
            New Project
          </button>
        )}
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Project</th>
            <th>Status</th>
            <th>Default</th>
            <th>Start</th>
            <th>End</th>
            {isAdmin && <th />}
          </tr>
        </thead>
        <tbody>
          {sorted.map((project) => (
            <tr key={project.id}>
              <td>{projectLabel(project)}</td>
              <td>
                <ProjectStatusBadge status={project.status} />
              </td>
              <td>{project.is_default ? "Current" : "—"}</td>
              <td>{formatDate(project.start_date)}</td>
              <td>{formatDate(project.end_date)}</td>
              {isAdmin && (
                <td className="data-table__actions">
                  {EDITABLE_STATUSES.includes(project.status) && (
                    <button
                      type="button"
                      className="button"
                      onClick={() => setModalProject(project)}
                    >
                      Edit
                    </button>
                  )}
                  {EDITABLE_STATUSES.includes(project.status) && sorted.length > 1 && (
                    <button
                      type="button"
                      className="button"
                      onClick={() => setCopyMembersProject(project)}
                    >
                      Copy Members
                    </button>
                  )}
                  {actionsFor(project).map((action) => (
                    <button
                      key={action.status}
                      type="button"
                      className="button"
                      disabled={statusMutation.isPending}
                      onClick={() => {
                        const message = CONFIRM_MESSAGES[action.status](project);
                        if (confirm(message)) {
                          statusMutation.mutate({ id: project.id, status: action.status });
                        }
                      }}
                    >
                      {action.label}
                    </button>
                  ))}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {modalProject !== undefined && (
        <ProjectFormModal
          project={modalProject}
          existingProjects={sorted}
          submitting={createMutation.isPending || updateMutation.isPending}
          errorMessage={formError}
          onClose={closeModal}
          onSubmit={(payload) => {
            setFormError(null);
            if (modalProject) {
              updateMutation.mutate({ id: modalProject.id, payload: payload as ProjectUpdatePayload });
            } else {
              createMutation.mutate(payload as ProjectCreatePayload);
            }
          }}
        />
      )}

      {copyMembersProject && (
        <CopyMembersModal
          targetProject={copyMembersProject}
          sourceCandidates={sorted.filter((p) => p.id !== copyMembersProject.id)}
          onClose={() => setCopyMembersProject(undefined)}
        />
      )}
    </div>
  );
}
