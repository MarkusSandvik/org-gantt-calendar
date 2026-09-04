import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Project } from "../api/types";
import { PagePlaceholder } from "../components/layout/PagePlaceholder";

export function Dashboard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });

  return (
    <PagePlaceholder
      title="Dashboard"
      phaseNote="Full dashboard (week summary, milestones, attention required) arrives in Phase 9."
    >
      <div className="connection-check">
        <h2>Backend connection</h2>
        {isLoading && <p>Checking connection to API...</p>}
        {isError && (
          <p className="connection-check__error">
            Could not reach the API: {(error as Error).message}
          </p>
        )}
        {data && data.length === 0 && <p>Connected — no project seeded yet.</p>}
        {data && data.length > 0 && (
          <ul>
            {data.map((project) => (
              <li key={project.id}>
                <strong>{project.name}</strong> — {project.start_date} to{" "}
                {project.end_date}
              </li>
            ))}
          </ul>
        )}
      </div>
    </PagePlaceholder>
  );
}
