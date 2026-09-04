import type { Milestone } from "../../api/types";
import { dateToX, parseISODate, type ZoomLevel } from "./dateScale";

interface MilestoneMarkerProps {
  milestone: Milestone;
  rangeStart: Date;
  zoom: ZoomLevel;
  onClick?: () => void;
}

export function MilestoneMarker({ milestone, rangeStart, zoom, onClick }: MilestoneMarkerProps) {
  const x = dateToX(parseISODate(milestone.date), rangeStart, zoom);
  const tooltip = [
    milestone.title,
    milestone.status.replace("_", " "),
    milestone.date,
    milestone.team ? `Team: ${milestone.team.name}` : null,
    onClick ? "Click to reschedule" : null,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div
      className={`gantt-milestone gantt-milestone--${milestone.status}${onClick ? " gantt-milestone--clickable" : ""}`}
      style={{ left: x }}
      title={tooltip}
      onClick={onClick}
    >
      <span className="gantt-milestone__diamond" />
      <span className="gantt-milestone__label">{milestone.title}</span>
    </div>
  );
}
