import type { Tag, Team } from "../../api/types";
import { ORGANIZATION_TEAM_FILTER } from "../../hooks/useCalendarFilters";

interface CalendarFilterBarProps {
  teams: Team[];
  tags: Tag[];
  teamFilter: string;
  tagFilter: string;
  onTeamChange: (value: string) => void;
  onTagChange: (value: string) => void;
}

export function CalendarFilterBar({
  teams,
  tags,
  teamFilter,
  tagFilter,
  onTeamChange,
  onTagChange,
}: CalendarFilterBarProps) {
  return (
    <div className="filter-bar">
      <select value={teamFilter} onChange={(e) => onTeamChange(e.target.value)}>
        <option value="">All teams</option>
        <option value={ORGANIZATION_TEAM_FILTER}>Organization</option>
        {teams.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
      <select value={tagFilter} onChange={(e) => onTagChange(e.target.value)}>
        <option value="">All tags</option>
        {tags.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
    </div>
  );
}
