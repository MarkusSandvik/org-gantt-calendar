import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export interface ActivityFilterState {
  q: string;
  teamId: string;
  ownerUserId: string;
  contributorUserId: string;
  tagId: string;
  status: string;
  priority: string;
  dateFrom: string;
  dateTo: string;
}

const EMPTY: ActivityFilterState = {
  q: "",
  teamId: "",
  ownerUserId: "",
  contributorUserId: "",
  tagId: "",
  status: "",
  priority: "",
  dateFrom: "",
  dateTo: "",
};

const PARAM_KEYS: Record<keyof ActivityFilterState, string> = {
  q: "q",
  teamId: "team_id",
  ownerUserId: "owner_user_id",
  contributorUserId: "contributor_user_id",
  tagId: "tag_id",
  status: "status",
  priority: "priority",
  dateFrom: "date_from",
  dateTo: "date_to",
};

/**
 * URL-search-param-backed activity filter state, shared by every view that
 * filters activities (Gantt, Admin > Activities, …). Keeping filters in the
 * URL makes them shareable/bookmarkable and lets global search results link
 * straight into a pre-filtered view.
 */
export function useActivityFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: ActivityFilterState = useMemo(() => {
    const result = { ...EMPTY };
    for (const key of Object.keys(PARAM_KEYS) as (keyof ActivityFilterState)[]) {
      result[key] = searchParams.get(PARAM_KEYS[key]) ?? "";
    }
    return result;
  }, [searchParams]);

  function setFilter(patch: Partial<ActivityFilterState>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch) as [
      keyof ActivityFilterState,
      string,
    ][]) {
      const paramKey = PARAM_KEYS[key];
      if (value) {
        next.set(paramKey, value);
      } else {
        next.delete(paramKey);
      }
    }
    setSearchParams(next, { replace: true });
  }

  function reset() {
    const next = new URLSearchParams(searchParams);
    for (const paramKey of Object.values(PARAM_KEYS)) {
      next.delete(paramKey);
    }
    setSearchParams(next, { replace: true });
  }

  const isActive = Object.values(filters).some((v) => v !== "");

  /** Build a backend query string from the current filters, plus any extra params. */
  function toQueryString(extra?: Record<string, string | number | undefined>): string {
    const params = new URLSearchParams();
    for (const [key, paramKey] of Object.entries(PARAM_KEYS) as [
      keyof ActivityFilterState,
      string,
    ][]) {
      const value = filters[key];
      if (value) params.set(paramKey, value);
    }
    if (extra) {
      for (const [k, v] of Object.entries(extra)) {
        if (v !== undefined && v !== "") params.set(k, String(v));
      }
    }
    return params.toString();
  }

  return { filters, setFilter, reset, isActive, toQueryString };
}
