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
}
