import type { Milestone } from "../../api/types";
import { dateToX, parseISODate, type ZoomLevel } from "./dateScale";

interface MilestoneMarkerProps {
  milestone: Milestone;
  rangeStart: Date;
  zoom: ZoomLevel;
}

export function MilestoneMarker({ milestone, rangeStart, zoom }: MilestoneMarkerProps) {
  const x = dateToX(parseISODate(milestone.date), rangeStart, zoom);
  const tooltip = [
    milestone.title,
    milestone.status.replace("_", " "),
    milestone.date,
    milestone.team ? `Team: ${milestone.team.name}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div
      className={`gantt-milestone gantt-milestone--${milestone.status}`}
      style={{ left: x }}
      title={tooltip}
    >
      <span className="gantt-milestone__diamond" />
      <span className="gantt-milestone__label">{milestone.title}</span>
    </div>
  );
}
