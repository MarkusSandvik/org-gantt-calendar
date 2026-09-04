export interface Project {
  id: number;
  name: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  auto_scheduling_enabled: boolean;
}

export type TeamCategory = "hardware" | "software" | "organization";

export interface Team {
  id: number;
  project_id: number;
  name: string;
  category: TeamCategory;
  color: string | null;
  sort_order: number;
}

export type UserRole = "viewer" | "editor" | "admin";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  active: boolean;
}

export interface Tag {
  id: number;
  project_id: number;
  name: string;
  color: string | null;
}

export type ActivityStatus =
  | "not_started"
  | "in_progress"
  | "completed"
  | "delayed"
  | "blocked";

export type Priority = "low" | "normal" | "high" | "critical";

export interface ActivityRef {
  id: number;
  name: string;
}

export interface ActivityTagRef {
  id: number;
  name: string;
  color: string | null;
}

export interface Activity {
  id: number;
  project_id: number;
  title: string;
  description: string | null;
  start_date: string;
  end_date: string;
  status: ActivityStatus;
  progress_percent: number;
  priority: Priority;
  owner_team: ActivityRef | null;
  owner_user: ActivityRef | null;
  created_by: ActivityRef | null;
  contributors: ActivityRef[];
  tags: ActivityTagRef[];
  created_at: string;
  updated_at: string;
}

export type MilestoneStatus = "not_started" | "on_track" | "at_risk" | "completed" | "missed";

export interface Milestone {
  id: number;
  project_id: number;
  title: string;
  description: string | null;
  date: string;
  status: MilestoneStatus;
  team: ActivityRef | null;
  owner_user: ActivityRef | null;
  tags: ActivityTagRef[];
}

export interface MilestoneWritePayload {
  project_id: number;
  title: string;
  description: string | null;
  date: string;
  status: MilestoneStatus;
  team_id: number | null;
  owner_user_id: number | null;
  tag_ids: number[];
  reason?: string;
}

export type SchedulableType = "activity" | "milestone";
export type DependencyType = "finish_to_start";

export interface Dependency {
  id: number;
  predecessor_type: SchedulableType;
  predecessor_id: number;
  predecessor_label: string;
  successor_type: SchedulableType;
  successor_id: number;
  successor_label: string;
  dependency_type: DependencyType;
  lag_days: number;
}

export interface DependencyWritePayload {
  predecessor_type: SchedulableType;
  predecessor_id: number;
  successor_type: SchedulableType;
  successor_id: number;
  dependency_type: DependencyType;
  lag_days: number;
}

export interface ScheduleChangeItem {
  entity_type: SchedulableType;
  entity_id: number;
  label: string;
  old_start_date: string;
  old_end_date: string;
  new_start_date: string;
  new_end_date: string;
  delta_days: number;
}

export interface SchedulingApplyResponse {
  change_group_id: string;
  changes: ScheduleChangeItem[];
}

export interface SchedulingChangeRequest {
  entity_type: SchedulableType;
  entity_id: number;
  new_start_date: string;
  new_end_date: string;
  reason?: string;
}

export type CalendarEventType =
  | "meeting"
  | "social"
  | "deadline"
  | "workshop"
  | "recruitment"
  | "sponsor"
  | "travel"
  | "presentation"
  | "stand_duty"
  | "other";

export interface CalendarEventRef {
  id: number;
  title: string;
}

export interface CalendarEvent {
  id: number;
  project_id: number;
  title: string;
  description: string | null;
  event_type: CalendarEventType;
  start_datetime: string;
  end_datetime: string;
  all_day: boolean;
  location: string | null;
  team: ActivityRef | null;
  owner_user: ActivityRef | null;
  related_activity: CalendarEventRef | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarEventWritePayload {
  project_id: number;
  title: string;
  description: string | null;
  event_type: CalendarEventType;
  start_datetime: string;
  end_datetime: string;
  all_day: boolean;
  location: string | null;
  team_id: number | null;
  owner_user_id: number | null;
  related_activity_id: number | null;
}

export interface WeekCounts {
  active_tasks: number;
  milestones_this_week: number;
  delayed: number;
  blocked: number;
  social_activities: number;
  meetings: number;
  upcoming_deadlines: number;
}

export interface DashboardUpcomingMilestone {
  id: number;
  title: string;
  date: string;
  team: string | null;
}

export interface DashboardAttentionItem {
  id: number;
  title: string;
  status: ActivityStatus;
  detail: string;
}

export interface DashboardSummary {
  iso_year: number;
  iso_week: number;
  week_start: string;
  week_end: string;
  week_counts: WeekCounts;
  upcoming_milestones: DashboardUpcomingMilestone[];
  attention_required: DashboardAttentionItem[];
}

export interface Comment {
  id: number;
  author: ActivityRef;
  body: string;
  created_at: string;
  status_change_from: string | null;
  status_change_to: string | null;
}

export interface CommentWritePayload {
  body: string;
}

export interface AuditLogEntry {
  id: number;
  user: ActivityRef;
  timestamp: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  change_group_id: string | null;
}

export interface Baseline {
  id: number;
  project_id: number;
  name: string;
  note: string | null;
  created_by: ActivityRef;
  created_at: string;
}

export interface BaselineCreatePayload {
  name: string;
  note: string | null;
}

export interface BaselineDriftItem {
  entity_type: "activity" | "milestone";
  entity_id: number;
  label: string;
  baseline_start: string;
  baseline_end: string;
  current_start: string;
  current_end: string;
  delta_start_days: number;
  delta_end_days: number;
}

export interface BaselineComparison {
  baseline: Baseline;
  items: BaselineDriftItem[];
}

export type SearchResultType = "activity" | "milestone" | "team" | "tag" | "user";

export interface SearchResult {
  type: SearchResultType;
  id: number;
  label: string;
  subtitle: string | null;
}

export interface ActivityWritePayload {
  project_id: number;
  title: string;
  description: string | null;
  start_date: string;
  end_date: string;
  status: ActivityStatus;
  progress_percent: number;
  priority: Priority;
  owner_team_id: number | null;
  owner_user_id: number | null;
  contributor_user_ids: number[];
  tag_ids: number[];
  reason?: string;
}
