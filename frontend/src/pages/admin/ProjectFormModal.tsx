import { useState } from "react";
import type { Project, ProjectCreatePayload, ProjectUpdatePayload } from "../../api/types";
import { projectLabel } from "../../components/ProjectStatusBadge";

interface ProjectFormModalProps {
  project: Project | null;
  existingProjects: Project[];
  onSubmit: (payload: ProjectCreatePayload | ProjectUpdatePayload) => void;
  onClose: () => void;
  submitting: boolean;
  errorMessage: string | null;
}

export function ProjectFormModal({
  project,
  existingProjects,
  onSubmit,
  onClose,
  submitting,
  errorMessage,
}: ProjectFormModalProps) {
  const [name, setName] = useState(project?.name ?? "");
  const [seasonLabel, setSeasonLabel] = useState(project?.season_label ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [startDate, setStartDate] = useState(project?.start_date ?? "");
  const [endDate, setEndDate] = useState(project?.end_date ?? "");
  const [copyFromId, setCopyFromId] = useState("");

  const copyableProjects = existingProjects.filter((p) => p.id !== project?.id);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{project ? "Edit Project" : "New Project"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (project) {
              onSubmit({
                name,
                season_label: seasonLabel || null,
                description: description || null,
                start_date: startDate || null,
                end_date: endDate || null,
              });
            } else {
              onSubmit({
                name,
                season_label: seasonLabel || undefined,
                description: description || null,
                start_date: startDate || null,
                end_date: endDate || null,
                copy_structure_from_project_id: copyFromId ? Number(copyFromId) : null,
              });
            }
          }}
        >
          <label>
            Name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
              placeholder="Team 28"
            />
          </label>
          <label>
            Season label
            <input
              value={seasonLabel}
              onChange={(e) => setSeasonLabel(e.target.value)}
              maxLength={50}
              placeholder="2027/28"
            />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </label>
          <label>
            Start date
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            End date
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
          {!project && copyableProjects.length > 0 && (
            <label>
              Copy teams &amp; tags from
              <select value={copyFromId} onChange={(e) => setCopyFromId(e.target.value)}>
                <option value="">Start empty</option>
                {copyableProjects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {projectLabel(p)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {!project && (
            <p className="page__phase-note">
              The new project starts in Draft. Activities, milestones, events, dependencies,
              baselines, and team memberships never carry over — only team and tag structure
              does, and only if you pick a project to copy from.
            </p>
          )}

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <div className="modal-actions">
            <div className="modal-actions__spacer" />
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button button--primary" disabled={submitting}>
              {project ? "Save changes" : "Create project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
