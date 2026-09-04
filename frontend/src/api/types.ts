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
