import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Team } from "../api/types";
import { PagePlaceholder } from "../components/layout/PagePlaceholder";

const ADMIN_SECTIONS = [
  "Activities",
  "Teams",
  "Tags",
  "Users",
  "Dependencies",
  "Baselines",
  "Import / Export",
  "Settings",
];

export function Admin() {
  const { data: teams } = useQuery({
    queryKey: ["teams"],
    queryFn: () => api.get<Team[]>("/teams"),
  });

  return (
    <PagePlaceholder
      title="Admin"
      phaseNote="Activity, milestone, dependency and tag management arrive across Phases 2, 5 and 8."
    >
      <div className="admin-sections">
        <h2>Planned sections</h2>
        <ul>
          {ADMIN_SECTIONS.map((section) => (
            <li key={section}>{section}</li>
          ))}
        </ul>
      </div>
      {teams && teams.length > 0 && (
        <div className="admin-sections">
          <h2>Seeded teams ({teams.length})</h2>
          <ul>
            {teams.map((team) => (
              <li key={team.id}>
                {team.name} <span className="tag-chip">{team.category}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </PagePlaceholder>
  );
}
