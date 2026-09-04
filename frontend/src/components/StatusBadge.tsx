import type { ActivityStatus } from "../api/types";

const LABELS: Record<ActivityStatus, string> = {
  not_started: "Not Started",
  in_progress: "In Progress",
  completed: "Completed",
  delayed: "Delayed",
  blocked: "Blocked",
};

export function StatusBadge({ status }: { status: ActivityStatus }) {
  return <span className={`status-badge status-badge--${status}`}>{LABELS[status]}</span>;
}
