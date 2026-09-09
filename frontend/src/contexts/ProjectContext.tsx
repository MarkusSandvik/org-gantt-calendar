import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api/client";
import type { Project } from "../api/types";

const STORAGE_KEY = "current-project-id";

function readStoredProjectId(): number | null {
  const stored = localStorage.getItem(STORAGE_KEY);
  const parsed = stored ? Number(stored) : NaN;
  return Number.isFinite(parsed) ? parsed : null;
}

interface ProjectContextValue {
  /** The current project, or null while the project list is still loading
   * (or if the org has no projects at all, which shouldn't happen once
   * seeded). Every project-scoped page reads its project id from here
   * instead of independently fetching /projects and guessing. */
  project: Project | null;
  projects: Project[];
  isLoading: boolean;
  /** False for a COMPLETED or ARCHIVED project — pages should disable
   * creation/editing controls (but still render everything read-only). */
  canEdit: boolean;
  switchProject: (projectId: number) => void;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const [selectedId, setSelectedId] = useState<number | null>(() => readStoredProjectId());

  // The URL's leading segment (e.g. "/auv-2026/gantt" -> "auv-2026") wins
  // over the stored selection whenever it matches a real project, so a
  // deep-linked or bookmarked project URL always shows that project rather
  // than whatever was last selected on this device.
  const location = useLocation();
  const urlSlug = location.pathname.split("/")[1] || null;

  const project = useMemo<Project | null>(() => {
    if (!projects || projects.length === 0) return null;
    const byUrl = urlSlug ? projects.find((p) => p.slug === urlSlug) : undefined;
    if (byUrl) return byUrl;
    const bySelection = selectedId != null ? projects.find((p) => p.id === selectedId) : undefined;
    if (bySelection) return bySelection;
    return projects.find((p) => p.is_default) ?? projects[0];
  }, [projects, urlSlug, selectedId]);

  // Remember the resolved project (not just what the user explicitly
  // picked) so a fresh login lands back where they left off per Section 30,
  // even if they never opened the switcher this session.
  useEffect(() => {
    if (project) localStorage.setItem(STORAGE_KEY, String(project.id));
  }, [project]);

  const canEdit = project ? project.status === "draft" || project.status === "active" : false;

  return (
    <ProjectContext.Provider
      value={{
        project,
        projects: projects ?? [],
        isLoading,
        canEdit,
        switchProject: setSelectedId,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used within a ProjectProvider");
  return ctx;
}
