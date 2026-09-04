import type { ActivityFilterState } from "../../hooks/useActivityFilters";
import type { ActivityStatus, Priority, Tag, Team, User } from "../../api/types";

const STATUS_OPTIONS: ActivityStatus[] = [
  "not_started",
  "in_progress",
  "completed",
  "delayed",
  "blocked",
];

const PRIORITY_OPTIONS: Priority[] = ["low", "normal", "high", "critical"];

interface FilterBarProps {
  filters: ActivityFilterState;
  onChange: (patch: Partial<ActivityFilterState>) => void;
  onReset: () => void;
  isActive: boolean;
  teams: Team[];
  users: User[];
  tags: Tag[];
}

export function FilterBar({
  filters,
  onChange,
  onReset,
  isActive,
  teams,
  users,
  tags,
}: FilterBarProps) {
  return (
    <div className="filter-bar">
      <input
        className="filter-bar__search"
        placeholder="Search title..."
        value={filters.q}
        onChange={(e) => onChange({ q: e.target.value })}
      />
      <select value={filters.teamId} onChange={(e) => onChange({ teamId: e.target.value })}>
        <option value="">All teams</option>
        {teams.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
      <select
        value={filters.ownerUserId}
        onChange={(e) => onChange({ ownerUserId: e.target.value })}
      >
        <option value="">All owners</option>
        {users.map((u) => (
          <option key={u.id} value={u.id}>
            {u.name}
          </option>
        ))}
      </select>
      <select
        value={filters.contributorUserId}
        onChange={(e) => onChange({ contributorUserId: e.target.value })}
      >
        <option value="">All contributors</option>
        {users.map((u) => (
          <option key={u.id} value={u.id}>
            {u.name}
          </option>
        ))}
      </select>
      <select value={filters.tagId} onChange={(e) => onChange({ tagId: e.target.value })}>
        <option value="">All tags</option>
        {tags.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
      <select value={filters.status} onChange={(e) => onChange({ status: e.target.value })}>
        <option value="">All statuses</option>
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s.replace("_", " ")}
          </option>
        ))}
      </select>
      <select
        value={filters.priority}
        onChange={(e) => onChange({ priority: e.target.value })}
      >
        <option value="">All priorities</option>
        {PRIORITY_OPTIONS.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
      <input
        type="date"
        title="From date"
        value={filters.dateFrom}
        onChange={(e) => onChange({ dateFrom: e.target.value })}
      />
      <input
        type="date"
        title="To date"
        value={filters.dateTo}
        onChange={(e) => onChange({ dateTo: e.target.value })}
      />
      <button
        type="button"
        className={
          filters.status === "delayed" ? "chip-toggle chip-toggle--active" : "chip-toggle"
        }
        onClick={() => onChange({ status: filters.status === "delayed" ? "" : "delayed" })}
      >
        Delayed only
      </button>
      <button
        type="button"
        className={
          filters.status === "blocked" ? "chip-toggle chip-toggle--active" : "chip-toggle"
        }
        onClick={() => onChange({ status: filters.status === "blocked" ? "" : "blocked" })}
      >
        Blocked only
      </button>
      {isActive && (
        <button type="button" className="button" onClick={onReset}>
          Clear filters
        </button>
      )}
    </div>
  );
}
