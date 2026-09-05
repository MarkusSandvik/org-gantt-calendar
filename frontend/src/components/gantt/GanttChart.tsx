import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import type { Activity, Dependency, Milestone, Project, Tag, Team, User } from "../../api/types";
import { FilterBar } from "../filters/FilterBar";
import { useActivityFilters } from "../../hooks/useActivityFilters";
import { usePermissions } from "../../hooks/usePermissions";
import { DependencyArrows } from "./DependencyArrows";
import { GanttBar } from "./GanttBar";
import { MilestoneMarker } from "./MilestoneMarker";
import { RescheduleModal } from "./RescheduleModal";
import { TimelineHeader } from "./TimelineHeader";
import { buildRowIndex, GROUP_HEADER_HEIGHT, ROW_HEIGHT } from "./rowLayout";
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
  const unassigned: Activity[] = [];
  for (const activity of activities) {
    if (activity.owner_team) {
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
  if (unassigned.length > 0) {
    groups.push({
      key: "unassigned",
      label: "Unassigned",
      activities: unassigned.sort((a, b) => a.start_date.localeCompare(b.start_date)),
    });
  }
  return groups;
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
  const [reschedule, setReschedule] = useState<RescheduleTarget | null>(null);
  const { filters, setFilter, reset, isActive, toQueryString } = useActivityFilters();
  const { canEditActivity, canManageMilestone } = usePermissions();

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const project = projects?.[0];
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
    queryKey: ["dependencies"],
    queryFn: () => api.get<Dependency[]>("/dependencies"),
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
    const end = new Date(Math.max(...dates.map((d) => d.getTime())));
    return { start: addDays(start, -3), end: addDays(end, 3) };
  }, [project, allActivities, allMilestones]);

  const groups = useMemo(
    () => buildGroups(activities ?? [], teams ?? []),
    [activities, teams],
  );

  const rowIndex = useMemo(() => {
    if (!range) return null;
    return buildRowIndex(milestones ?? [], groups, range.start, zoom);
  }, [milestones, groups, range, zoom]);

  if (!project || !range) {
    return <p>Loading Gantt data...</p>;
  }

  const totalWidth = timelineWidth(range.start, range.end, zoom);

  const today = new Date();
  const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const showToday = todayMidnight >= range.start && todayMidnight <= range.end;
  const todayX = showToday ? dateToX(todayMidnight, range.start, zoom) : 0;

  const noResults =
    isActive &&
    (activities?.length ?? 0) === 0 &&
    (milestones?.length ?? 0) === 0;

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
      </div>

      {noResults ? (
        <p>No activities or milestones match these filters.</p>
      ) : (
        <div className="gantt-viewport">
          <div className="gantt-grid" style={{ width: LABEL_WIDTH + totalWidth }}>
            <TimelineHeader
              rangeStart={range.start}
              rangeEnd={range.end}
              zoom={zoom}
              labelWidth={LABEL_WIDTH}
              onWeekClick={(isoYear, isoWeek) => navigate(`/calendar/week/${isoYear}/${isoWeek}`)}
            />

            <div className="gantt-body" style={{ position: "relative" }}>
              {showToday && (
                <div
                  className="gantt-today-line"
                  style={{ left: LABEL_WIDTH + todayX }}
                  title={`Today — ${todayMidnight.toLocaleDateString("en-GB")}`}
                />
              )}

              {milestones && milestones.length > 0 && (
                <div className="gantt-group">
                  <div
                    className="gantt-group__header"
                    style={{ width: LABEL_WIDTH + totalWidth, height: GROUP_HEADER_HEIGHT }}
                  >
                    <span className="gantt-group__header-text">Milestones</span>
                  </div>
                  {milestones.map((m) => (
                    <div key={m.id} className="gantt-row" style={{ height: ROW_HEIGHT }}>
                      <div className="gantt-row__label" style={{ width: LABEL_WIDTH }}>
                        {m.title}
                      </div>
                      <div className="gantt-row__track" style={{ width: totalWidth }}>
                        <MilestoneMarker
                          milestone={m}
                          rangeStart={range.start}
                          zoom={zoom}
                          onClick={
                            canManageMilestone(m)
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
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {groups.map((group) => (
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
                      </div>
                      <div className="gantt-row__track" style={{ width: totalWidth }}>
                        <GanttBar
                          activity={activity}
                          rangeStart={range.start}
                          zoom={zoom}
                          onClick={
                            canEditActivity(activity)
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
