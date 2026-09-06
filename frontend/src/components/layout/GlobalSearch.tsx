import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import type { SearchResult, SearchResultType } from "../../api/types";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

const TYPE_LABELS: Record<SearchResultType, string> = {
  activity: "Activities",
  milestone: "Milestones",
  team: "Teams",
  tag: "Tags",
  user: "Users",
};

const TYPE_ORDER: SearchResultType[] = ["activity", "milestone", "team", "tag", "user"];

function groupByType(results: SearchResult[]): [SearchResultType, SearchResult[]][] {
  const groups = new Map<SearchResultType, SearchResult[]>();
  for (const result of results) {
    const list = groups.get(result.type) ?? [];
    list.push(result);
    groups.set(result.type, list);
  }
  return TYPE_ORDER.filter((t) => groups.has(t)).map((t) => [t, groups.get(t)!]);
}

function isTypingTarget(element: Element | null): boolean {
  if (!element) return false;
  const tag = element.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || element.hasAttribute("contenteditable");
}

export function GlobalSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const debouncedQuery = useDebouncedValue(query, 250);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTypingTarget(document.activeElement)) return;
      e.preventDefault();
      inputRef.current?.focus();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const { data: results } = useQuery({
    queryKey: ["search", debouncedQuery],
    queryFn: () => api.get<SearchResult[]>(`/search?q=${encodeURIComponent(debouncedQuery)}`),
    enabled: debouncedQuery.trim().length >= 2,
  });

  function select(result: SearchResult) {
    setQuery("");
    setOpen(false);
    switch (result.type) {
      case "activity":
        navigate(`/admin/activities?q=${encodeURIComponent(result.label)}`);
        break;
      case "milestone":
        navigate(`/gantt?q=${encodeURIComponent(result.label)}`);
        break;
      case "team":
        navigate(`/admin/activities?team_id=${result.id}`);
        break;
      case "tag":
        navigate(`/admin/activities?tag_id=${result.id}`);
        break;
      case "user":
        navigate(`/admin/activities?owner_user_id=${result.id}`);
        break;
    }
  }

  const showDropdown = open && debouncedQuery.trim().length >= 2;
  const grouped = results ? groupByType(results) : [];

  return (
    <div className="global-search">
      <input
        ref={inputRef}
        className="global-search__input"
        placeholder="Search activities, milestones, teams, tags, people..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setOpen(false);
            inputRef.current?.blur();
          }
        }}
      />
      {!open && !query && <kbd className="global-search__shortcut-hint">/</kbd>}
      {showDropdown && (
        <div className="global-search__dropdown">
          {grouped.length === 0 && (
            <div className="global-search__empty">No matches for "{debouncedQuery}"</div>
          )}
          {grouped.map(([type, items]) => (
            <div key={type} className="global-search__group">
              <div className="global-search__group-label">{TYPE_LABELS[type]}</div>
              {items.map((item) => (
                <button
                  key={`${item.type}-${item.id}`}
                  type="button"
                  className="global-search__result"
                  onMouseDown={() => select(item)}
                >
                  <span className="global-search__result-label">{item.label}</span>
                  {item.subtitle && (
                    <span className="global-search__result-subtitle">{item.subtitle}</span>
                  )}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
