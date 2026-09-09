import { useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import type { Activity, Dependency, Milestone, Tag, Team, User } from "../../api/types";
import { FilterBar } from "../filters/FilterBar";
import { useProject } from "../../contexts/ProjectContext";
import { useActivityFilters } from "../../hooks/useActivityFilters";
import { usePermissions } from "../../hooks/usePermissions";
import { DependencyArrows } from "./DependencyArrows";
import { GanttBar } from "./GanttBar";
import { MilestoneMarker } from "./MilestoneMarker";
import { RescheduleModal } from "./RescheduleModal";
import { TimelineHeader } from "./TimelineHeader";
import {
  assignMilestoneLanes,
  buildRowIndex,
  estimateMilestoneOverflowDays,
  GROUP_HEADER_HEIGHT,
  ROW_HEIGHT,
} from "./rowLayout";
import {
  addDays,
  dateToX,
  parseISODate,
  timelineWidth,
  ZOOM_LEVELS,
  type ZoomLevel,
} from "./dateScale";

const LABEL_WIDTH = 240;

interface ActivityGroup {
  key: string;
  label: string;
  activities: Activity[];
}

function buildGroups(activities: Activity[], teams: Team[]): ActivityGroup[] {
  const byTeam = new Map<number, Activity[]>();
  const allTeams: Activity[] = [];
  const unassigned: Activity[] = [];
  for (const activity of activities) {
    if (activity.all_teams) {
      allTeams.push(activity);
    } else if (activity.owner_team) {
      const list = byTeam.get(activity.owner_team.id) ?? [];
      list.push(activity);
      byTeam.set(activity.owner_team.id, list);
    } else {
      unassigned.push(activity);
    }
  }

  const groups: ActivityGroup[] = [];
  for (const team of [...teams].sort((a, b) => a.sort_order - b.sort_order)) {
    const list = byTeam.get(team.id);
    if (list && list.length > 0) {
      groups.push({
        key: `team-${team.id}`,
        label: team.name,
        activities: [...list].sort((a, b) => a.start_date.localeCompare(b.start_date)),
      });
    }
  }
  if (allTeams.length > 0) {
    groups.push({
      key: "all-teams",
      label: "All Teams",
      activities: allTeams.sort((a, b) => a.start_date.localeCompare(b.start_date)),
    });
  }
  if (unassigned.length > 0) {
    groups.push({
      key: "unassigned",
      label: "Unassigned",
      activities: unassigned.sort((a, b) => a.start_date.localeCompare(b.start_date)),
    });
  }
  return groups;
}

type ViewMode = "team" | "timeline";

function buildTimelineGroup(activities: Activity[]): ActivityGroup {
  return {
    key: "timeline",
    label: "All Activities",
    activities: [...activities].sort((a, b) => a.start_date.localeCompare(b.start_date)),
  };
}

interface RescheduleTarget {
  entityType: "activity" | "milestone";
  entityId: number;
  label: string;
  startDate: string;
  endDate: string;
}

export function GanttChart() {
  const navigate = useNavigate();
  const [zoom, setZoom] = useState<ZoomLevel>("month");
  const [viewMode, setViewMode] = useState<ViewMode>("team");
  const [hiddenGroupKeys, setHiddenGroupKeys] = useState<Set<string>>(new Set());
  const [reschedule, setReschedule] = useState<RescheduleTarget | null>(null);
  const [exporting, setExporting] = useState(false);
  const gridRef = useRef<HTMLDivElement>(null);
  const { filters, setFilter, reset, isActive, toQueryString } = useActivityFilters();
  const { canEditActivity, canManageMilestone } = usePermissions();

  const { project, canEdit } = useProject();
  const projectId = project?.id;

  const { data: teams } = useQuery({
    queryKey: ["teams"],
    queryFn: () => api.get<Team[]>("/teams"),
  });
  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
  });
  const { data: tags } = useQuery({
    queryKey: ["tags"],
    queryFn: () => api.get<Tag[]>("/tags"),
  });

  // Unfiltered fetches, used only to keep the timeline's date range stable
  // regardless of which filters are active — narrowing a filter shouldn't
  // also rescale the whole chart.
  const { data: allActivities } = useQuery({
    queryKey: ["activities", "all", { projectId }],
    queryFn: () => api.get<Activity[]>(`/activities?project_id=${projectId}`),
    enabled: projectId != null,
  });
  const { data: allMilestones } = useQuery({
    queryKey: ["milestones", "all", { projectId }],
    queryFn: () => api.get<Milestone[]>(`/milestones?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const filterQuery = toQueryString({ project_id: projectId });
  const { data: activities } = useQuery({
    queryKey: ["activities", "filtered", filterQuery],
    queryFn: () => api.get<Activity[]>(`/activities?${filterQuery}`),
    enabled: projectId != null,
  });
  const { data: milestones } = useQuery({
    queryKey: ["milestones", "filtered", filterQuery],
    queryFn: () => api.get<Milestone[]>(`/milestones?${filterQuery}`),
    enabled: projectId != null,
  });
  const { data: dependencies } = useQuery({
    queryKey: ["dependencies", { projectId }],
    queryFn: () => api.get<Dependency[]>(`/dependencies?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const range = useMemo(() => {
    if (!project) return null;
    const dates: Date[] = [];
    if (project.start_date) dates.push(parseISODate(project.start_date));
    if (project.end_date) dates.push(parseISODate(project.end_date));
    for (const a of allActivities ?? []) {
      dates.push(parseISODate(a.start_date), parseISODate(a.end_date));
    }
    for (const m of allMilestones ?? []) {
      dates.push(parseISODate(m.date));
    }
    if (dates.length === 0) return null;
    const start = new Date(Math.min(...dates.map((d) => d.getTime())));
    let end = new Date(Math.max(...dates.map((d) => d.getTime())));
    // A milestone's label can render well past its own date — make sure the
    // range extends far enough that the last milestone's text isn't clipped
    // (most visible in the PNG export, which is sized to this exact range).
    for (const m of allMilestones ?? []) {
      const labelEnd = addDays(parseISODate(m.date), estimateMilestoneOverflowDays(m.title, zoom));
      if (labelEnd > end) end = labelEnd;
    }
    return { start: addDays(start, -3), end: addDays(end, 3) };
  }, [project, allActivities, allMilestones, zoom]);

  const groups = useMemo(
    () => buildGroups(activities ?? [], teams ?? []),
    [activities, teams],
  );

  const visibleGroups = useMemo(
    () => groups.filter((g) => !hiddenGroupKeys.has(g.key)),
    [groups, hiddenGroupKeys],
  );

  function toggleGroupVisibility(key: string) {
    setHiddenGroupKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const displayGroups = useMemo(() => {
    if (viewMode !== "timeline") return visibleGroups;
    return [buildTimelineGroup(visibleGroups.flatMap((g) => g.activities))];
  }, [viewMode, visibleGroups]);

  const showMilestones = !hiddenGroupKeys.has("milestones");
  const visibleMilestones = showMilestones ? milestones ?? [] : [];
  const allToggleKeys = [
    ...(allMilestones && allMilestones.length > 0 ? ["milestones"] : []),
    ...groups.map((g) => g.key),
  ];

  const milestoneLanes = useMemo(() => {
    if (!range) return [];
    return assignMilestoneLanes(visibleMilestones, range.start, zoom);
  }, [visibleMilestones, range, zoom]);

  const rowIndex = useMemo(() => {
    if (!range) return null;
    return buildRowIndex(visibleMilestones, displayGroups, range.start, zoom);
  }, [visibleMilestones, displayGroups, range, zoom]);

  if (!project || !range) {
    return <p>Loading Project Schedule data...</p>;
  }

  const projectName = project.name;
  const totalWidth = timelineWidth(range.start, range.end, zoom);

  const today = new Date();
  const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const showToday = todayMidnight >= range.start && todayMidnight <= range.end;
  const todayX = showToday ? dateToX(todayMidnight, range.start, zoom) : 0;

  const noResults =
    isActive &&
    (activities?.length ?? 0) === 0 &&
    (milestones?.length ?? 0) === 0;

  async function exportPng() {
    if (!gridRef.current) return;
    setExporting(true);
    try {
      const background = getComputedStyle(document.documentElement)
        .getPropertyValue("--color-surface")
        .trim();
      const dataUrl = await toPng(gridRef.current, { backgroundColor: background || "#ffffff" });
      const slug = projectName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const link = document.createElement("a");
      link.download = `${slug || "gantt"}-${new Date().toISOString().slice(0, 10)}.png`;
      link.href = dataUrl;
      link.click();
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="gantt">
      <FilterBar
        filters={filters}
        onChange={setFilter}
        onReset={reset}
        isActive={isActive}
        teams={teams ?? []}
        users={users ?? []}
        tags={tags ?? []}
      />

      {(groups.length > 1 || (allMilestones && allMilestones.length > 0)) && (
        <div className="gantt-group-filter">
          <span className="gantt-group-filter__label">Show groups:</span>
          {allMilestones && allMilestones.length > 0 && (
            <button
              type="button"
              className={showMilestones ? "chip-toggle chip-toggle--active" : "chip-toggle"}
              onClick={() => toggleGroupVisibility("milestones")}
            >
              Milestones
            </button>
          )}
          {groups.map((g) => (
            <button
              key={g.key}
              type="button"
              className={
                hiddenGroupKeys.has(g.key) ? "chip-toggle" : "chip-toggle chip-toggle--active"
              }
              onClick={() => toggleGroupVisibility(g.key)}
            >
              {g.label}
            </button>
          ))}
          {hiddenGroupKeys.size < allToggleKeys.length && (
            <button
              type="button"
              className="chip-toggle"
              onClick={() => setHiddenGroupKeys(new Set(allToggleKeys))}
            >
              Hide all
            </button>
          )}
          {hiddenGroupKeys.size > 0 && (
            <button
              type="button"
              className="chip-toggle"
              onClick={() => setHiddenGroupKeys(new Set())}
            >
              Show all
            </button>
          )}
        </div>
      )}

      <div className="gantt-toolbar">
        <div className="gantt-legend">
          <span className="gantt-legend__item">
            <span className="gantt-legend__swatch gantt-legend__swatch--not_started" /> Not started
          </span>
          <span className="gantt-legend__item">
            <span className="gantt-legend__swatch gantt-legend__swatch--in_progress" /> In progress
          </span>
          <span className="gantt-legend__item">
            <span className="gantt-legend__swatch gantt-legend__swatch--completed" /> Completed
          </span>
          <span className="gantt-legend__item">
            <span className="gantt-legend__swatch gantt-legend__swatch--delayed" /> Delayed
          </span>
          <span className="gantt-legend__item">
            <span className="gantt-legend__swatch gantt-legend__swatch--blocked" /> Blocked
          </span>
        </div>
        <div className="zoom-control">
          <button
            className={viewMode === "team" ? "zoom-control__btn zoom-control__btn--active" : "zoom-control__btn"}
            onClick={() => setViewMode("team")}
          >
            By Team
          </button>
          <button
            className={viewMode === "timeline" ? "zoom-control__btn zoom-control__btn--active" : "zoom-control__btn"}
            onClick={() => setViewMode("timeline")}
          >
            Timeline
          </button>
        </div>
        <div className="zoom-control">
          {ZOOM_LEVELS.map((level) => (
            <button
              key={level}
              className={level === zoom ? "zoom-control__btn zoom-control__btn--active" : "zoom-control__btn"}
              onClick={() => setZoom(level)}
            >
              {level[0].toUpperCase() + level.slice(1)}
            </button>
          ))}
        </div>
        <button className="button" onClick={exportPng} disabled={exporting}>
          {exporting ? "Exporting..." : "Export as PNG"}
        </button>
        <button className="button" onClick={() => window.print()}>
          Print / Save as PDF
        </button>
      </div>

      {noResults ? (
        <p>No activities or milestones match these filters.</p>
      ) : (
        <div className="gantt-viewport">
          <div ref={gridRef} className="gantt-grid" style={{ width: LABEL_WIDTH + totalWidth }}>
            <TimelineHeader
              rangeStart={range.start}
              rangeEnd={range.end}
              zoom={zoom}
              labelWidth={LABEL_WIDTH}
              onWeekClick={(isoYear, isoWeek) =>
                navigate(`/${project?.slug}/calendar/week/${isoYear}/${isoWeek}`)
              }
            />

            <div className="gantt-body" style={{ position: "relative" }}>
              {showToday && (
                <div
                  className="gantt-today-line"
                  style={{ left: LABEL_WIDTH + todayX }}
                  title={`Today — ${todayMidnight.toLocaleDateString("en-GB")}`}
                />
              )}

              {visibleMilestones.length > 0 && (
                <div className="gantt-group">
                  <div
                    className="gantt-group__header"
                    style={{ width: LABEL_WIDTH + totalWidth, height: GROUP_HEADER_HEIGHT }}
                  >
                    <span className="gantt-group__header-text">Milestones</span>
                  </div>
                  {milestoneLanes.map((lane, laneIndex) => (
                    <div key={laneIndex} className="gantt-row" style={{ height: ROW_HEIGHT }}>
                      <div className="gantt-row__label" style={{ width: LABEL_WIDTH }} />
                      <div className="gantt-row__track" style={{ width: totalWidth }}>
                        {lane.map((m) => (
                          <MilestoneMarker
                            key={m.id}
                            milestone={m}
                            rangeStart={range.start}
                            zoom={zoom}
                            onClick={
                              canManageMilestone(m) && canEdit
                                ? () =>
                                    setReschedule({
                                      entityType: "milestone",
                                      entityId: m.id,
                                      label: m.title,
                                      startDate: m.date,
                                      endDate: m.date,
                                    })
                                : undefined
                            }
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {displayGroups.map((group) => (
                <div key={group.key} className="gantt-group">
                  <div
                    className="gantt-group__header"
                    style={{ width: LABEL_WIDTH + totalWidth, height: GROUP_HEADER_HEIGHT }}
                  >
                    <span className="gantt-group__header-text">{group.label}</span>
                  </div>
                  {group.activities.map((activity) => (
                    <div key={activity.id} className="gantt-row" style={{ height: ROW_HEIGHT }}>
                      <div className="gantt-row__label" style={{ width: LABEL_WIDTH }}>
                        {activity.title}
                        {viewMode === "timeline" && activity.all_teams && (
                          <span className="gantt-row__label-team"> · All Teams</span>
                        )}
                        {viewMode === "timeline" && !activity.all_teams && activity.owner_team && (
                          <span className="gantt-row__label-team"> · {activity.owner_team.name}</span>
                        )}
                      </div>
                      <div className="gantt-row__track" style={{ width: totalWidth }}>
                        <GanttBar
                          activity={activity}
                          rangeStart={range.start}
                          zoom={zoom}
                          onClick={
                            canEditActivity(activity) && canEdit
                              ? () =>
                                  setReschedule({
                                    entityType: "activity",
                                    entityId: activity.id,
                                    label: activity.title,
                                    startDate: activity.start_date,
                                    endDate: activity.end_date,
                                  })
                              : undefined
                          }
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ))}

              {rowIndex && dependencies && dependencies.length > 0 && (
                <DependencyArrows
                  dependencies={dependencies}
                  positions={rowIndex.positions}
                  labelWidth={LABEL_WIDTH}
                  width={LABEL_WIDTH + totalWidth}
                  height={rowIndex.totalHeight}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {reschedule && (
        <RescheduleModal
          entityType={reschedule.entityType}
          entityId={reschedule.entityId}
          label={reschedule.label}
          initialStartDate={reschedule.startDate}
          initialEndDate={reschedule.endDate}
          onClose={() => setReschedule(null)}
        />
      )}
    </div>
  );
}
