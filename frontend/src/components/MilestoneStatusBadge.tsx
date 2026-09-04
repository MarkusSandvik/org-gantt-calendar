import type { MilestoneStatus } from "../api/types";

const LABELS: Record<MilestoneStatus, string> = {
  not_started: "Not Started",
  on_track: "On Track",
  at_risk: "At Risk",
  completed: "Completed",
  missed: "Missed",
};

export function MilestoneStatusBadge({ status }: { status: MilestoneStatus }) {
  return (
    <span className={`milestone-status-badge milestone-status-badge--${status}`}>
      {LABELS[status]}
    </span>
  );
}
