import type { Project, ProjectStatus } from "../api/types";

const LABELS: Record<ProjectStatus, string> = {
  draft: "Draft",
  active: "Active",
  completed: "Completed",
  archived: "Archived",
};

export function ProjectStatusBadge({ status }: { status: ProjectStatus }) {
  return (
    <span className={`project-status-badge project-status-badge--${status}`}>
      {LABELS[status]}
    </span>
  );
}

export function projectLabel(project: Project): string {
  return project.season_label ? `${project.name} — ${project.season_label}` : project.name;
}
