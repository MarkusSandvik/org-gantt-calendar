import { useEffect, useState } from "react";
import type { Project } from "../api/types";

export const ORGANIZATION_TEAM_FILTER = "__all__";

export interface CalendarFilterState {
  teamFilter: string;
  tagFilter: string;
}

export interface CalendarFilterQueryParams {
  team_id?: number;
  all_teams_only?: boolean;
  tag_id?: number;
}

export function toCalendarQueryParams(filters: CalendarFilterState): CalendarFilterQueryParams {
  const params: CalendarFilterQueryParams = {};
  if (filters.teamFilter === ORGANIZATION_TEAM_FILTER) {
    params.all_teams_only = true;
  } else if (filters.teamFilter) {
    params.team_id = Number(filters.teamFilter);
  }
  if (filters.tagFilter) {
    params.tag_id = Number(filters.tagFilter);
  }
  return params;
}

/** Renders as a query-string suffix (e.g. "&team_id=3&tag_id=5"), matching
 * this codebase's existing template-literal query building rather than
 * introducing URLSearchParams just for this. */
export function calendarQuerySuffix(params: CalendarFilterQueryParams): string {
  let suffix = "";
  if (params.all_teams_only) suffix += "&all_teams_only=true";
  if (params.team_id != null) suffix += `&team_id=${params.team_id}`;
  if (params.tag_id != null) suffix += `&tag_id=${params.tag_id}`;
  return suffix;
}

function defaultTeamFilterFor(project: Project | null | undefined): string {
  if (!project || project.default_calendar_all_teams) return ORGANIZATION_TEAM_FILTER;
  return project.default_calendar_team_id?.toString() ?? "";
}

function defaultTagFilterFor(project: Project | null | undefined): string {
  return project?.default_calendar_tag_id?.toString() ?? "";
}

/** Calendar pages default to the project's Admin-configured default view
 * (Organization-wide events out of the box — the "Annual wheel" use case
 * discussed with the project owner) rather than every team's events at
 * once. `project` loads asynchronously, so the configured default is
 * applied once, the first time it becomes available, and never overwrites
 * a filter the viewer has since chosen themselves. */
export function useCalendarFilters(project?: Project | null) {
  const [teamFilter, setTeamFilter] = useState(() => defaultTeamFilterFor(project));
  const [tagFilter, setTagFilter] = useState(() => defaultTagFilterFor(project));
  const [appliedProjectDefault, setAppliedProjectDefault] = useState(project != null);

  useEffect(() => {
    if (project && !appliedProjectDefault) {
      setTeamFilter(defaultTeamFilterFor(project));
      setTagFilter(defaultTagFilterFor(project));
      setAppliedProjectDefault(true);
    }
  }, [project, appliedProjectDefault]);

  return {
    teamFilter,
    tagFilter,
    setTeamFilter,
    setTagFilter,
    queryParams: toCalendarQueryParams({ teamFilter, tagFilter }),
  };
}
