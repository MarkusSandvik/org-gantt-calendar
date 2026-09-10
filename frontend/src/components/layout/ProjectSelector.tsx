import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { Project } from "../../api/types";
import { useProject } from "../../contexts/ProjectContext";
import { ProjectStatusBadge, projectLabel } from "../ProjectStatusBadge";

export function ProjectSelector() {
  const { project, projects, switchProject } = useProject();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  if (!project) return null;

  function goToProject(target: Project) {
    switchProject(target.id);
    // Swap just the leading /:projectSlug segment so switching keeps you on
    // the equivalent page (e.g. /old-slug/gantt -> /new-slug/gantt).
    const rest = location.pathname.replace(/^\/[^/]+/, "");
    navigate(`/${target.slug}${rest}${location.search}`);
  }

  const others = projects
    .filter((p) => p.id !== project.id)
    .sort((a, b) => b.id - a.id);
  // A non-default project can still be genuinely active (e.g. mid
  // leadership handover, with two seasons running in parallel), not just
  // past history — split the list so the label stays accurate.
  const otherActive = others.filter((p) => p.status === "draft" || p.status === "active");
  const otherHistory = others.filter((p) => p.status === "completed" || p.status === "archived");

  return (
    <div className="project-selector">
      <button
        type="button"
        className="project-selector__trigger"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="project-selector__name">{projectLabel(project)}</span>
        <ProjectStatusBadge status={project.status} />
        <span className="project-selector__caret">▾</span>
      </button>

      {open && (
        <>
          <div className="project-selector__backdrop" onClick={() => setOpen(false)} />
          <div className="project-selector__menu">
            <div className="project-selector__group-label">Current</div>
            <div className="project-selector__item project-selector__item--active">
              <span>{projectLabel(project)}</span>
              <ProjectStatusBadge status={project.status} />
            </div>

            {otherActive.length > 0 && (
              <>
                <div className="project-selector__group-label">Other Active</div>
                {otherActive.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="project-selector__item"
                    onClick={() => {
                      goToProject(p);
                      setOpen(false);
                    }}
                  >
                    <span>{projectLabel(p)}</span>
                    <ProjectStatusBadge status={p.status} />
                  </button>
                ))}
              </>
            )}

            {otherHistory.length > 0 && (
              <>
                <div className="project-selector__group-label">History</div>
                {otherHistory.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="project-selector__item"
                    onClick={() => {
                      goToProject(p);
                      setOpen(false);
                    }}
                  >
                    <span>{projectLabel(p)}</span>
                    <ProjectStatusBadge status={p.status} />
                  </button>
                ))}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
