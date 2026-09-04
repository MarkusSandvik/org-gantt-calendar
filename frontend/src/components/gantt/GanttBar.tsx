import type { Activity } from "../../api/types";
import { addDays, dateToX, parseISODate, type ZoomLevel } from "./dateScale";

const MIN_BAR_WIDTH = 6;

interface GanttBarProps {
  activity: Activity;
  rangeStart: Date;
  zoom: ZoomLevel;
}

export function GanttBar({ activity, rangeStart, zoom }: GanttBarProps) {
  const start = parseISODate(activity.start_date);
  const end = parseISODate(activity.end_date);
  const left = dateToX(start, rangeStart, zoom);
  const width = Math.max(dateToX(addDays(end, 1), rangeStart, zoom) - left, MIN_BAR_WIDTH);

  const tooltip = [
    activity.title,
    `${activity.status.replace("_", " ")} · ${activity.progress_percent}%`,
    activity.owner_user ? `Owner: ${activity.owner_user.name}` : null,
    `${activity.start_date} → ${activity.end_date}`,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div
      className={`gantt-bar gantt-bar--${activity.status}`}
      style={{ left, width }}
      title={tooltip}
    >
      <div className="gantt-bar__progress" style={{ width: `${activity.progress_percent}%` }} />
      <span className="gantt-bar__label">{activity.title}</span>
    </div>
  );
}
