import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Project, ProjectCreatePayload, ProjectStatus } from "../../api/types";
import { ProjectStatusBadge, projectLabel } from "../../components/ProjectStatusBadge";
import { useToast } from "../../components/Toast";
import { usePermissions } from "../../hooks/usePermissions";
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
    `Activate "${projectLabel(p)}"? It becomes the default project everyone lands on, and the current active project (if any) is marked Completed.`,
  completed: (p) => `Mark "${projectLabel(p)}" as Completed?`,
  archived: (p) =>
    `Archive "${projectLabel(p)}"? This is permanent — an archived project can never be reactivated, and becomes fully read-only.`,
  draft: () => "",
};

function formatDate(iso: string | null): string {
  return iso ?? "—";
}

export function ProjectsAdmin() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { isAdmin } = usePermissions();

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });

  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (payload: ProjectCreatePayload) => api.post<Project>("/projects", payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setFormError(null);
      showToast(`"${projectLabel(created)}" created`);
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
          <button className="button button--primary" onClick={() => setShowForm(true)}>
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
                  {NEXT_STATUS_ACTIONS[project.status].map((action) => (
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

      {showForm && (
        <ProjectFormModal
          existingProjects={sorted}
          submitting={createMutation.isPending}
          errorMessage={formError}
          onClose={() => {
            setShowForm(false);
            setFormError(null);
          }}
          onSubmit={(payload) => {
            setFormError(null);
            createMutation.mutate(payload);
          }}
        />
      )}
    </div>
  );
}
