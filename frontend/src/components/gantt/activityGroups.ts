import type { Activity, Team } from "../../api/types";

export interface ActivityGroup {
  key: string;
  label: string;
  activities: Activity[];
}

/** Groups activities the same way the Gantt does — one group per team
 * (ordered by the team's own sort_order), then an "Organization" catch-all
 * for org-wide activities, then "Unassigned" for anything with neither.
 * Shared with the annual wheel so both views agree on team order/labels. */
export function buildGroups(activities: Activity[], teams: Team[]): ActivityGroup[] {
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
      label: "Organization",
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
