import type { Activity, Me, Milestone } from "../api/types";
import { useCurrentUser } from "./useAuth";

function isAdmin(me: Me | null): boolean {
  return me?.global_role === "admin";
}

function leadsTeam(me: Me | null, teamId: number | null | undefined): boolean {
  if (!me || teamId == null) return false;
  return me.team_memberships.some((m) => m.team_id === teamId && m.team_role === "lead");
}

function isLeadOfAnyTeam(me: Me | null): boolean {
  if (!me) return false;
  return me.team_memberships.some((m) => m.team_role === "lead");
}

function isAssignedToActivity(me: Me | null, activity: Activity): boolean {
  if (!me) return false;
  if (activity.owner_user?.id === me.id) return true;
  return activity.contributors.some((c) => c.id === me.id);
}

/** Mirrors backend/app/core/permissions.py — the frontend only uses this
 * to decide what to show; the backend re-checks everything server-side
 * regardless of what the UI allowed the user to attempt. */
export function usePermissions() {
  const { me } = useCurrentUser();

  return {
    me,
    isAdmin: isAdmin(me),
    isLeadOfAnyTeam: isLeadOfAnyTeam(me),
    leadsTeam: (teamId: number | null | undefined) => leadsTeam(me, teamId),

    canCreateActivityInTeam: (teamId: number | null | undefined) =>
      isAdmin(me) || leadsTeam(me, teamId),

    canEditActivity: (activity: Activity) =>
      isAdmin(me) || leadsTeam(me, activity.owner_team?.id),

    canUpdateAssignedFieldsOnly: (activity: Activity) =>
      !isAdmin(me) && !leadsTeam(me, activity.owner_team?.id) && isAssignedToActivity(me, activity),

    canCommentOnActivity: (activity: Activity) =>
      isAdmin(me) || leadsTeam(me, activity.owner_team?.id) || isAssignedToActivity(me, activity),

    canManageMilestone: (milestone: Pick<Milestone, "team">) =>
      isAdmin(me) || leadsTeam(me, milestone.team?.id),

    canCommentOnMilestone: (milestone: Milestone) =>
      isAdmin(me) || leadsTeam(me, milestone.team?.id) || milestone.owner_user?.id === me?.id,

    canManageCalendarEventInTeam: (teamId: number | null | undefined) =>
      isAdmin(me) || leadsTeam(me, teamId),

    canUseScheduling: isAdmin(me) || isLeadOfAnyTeam(me),

    canManageBaselines: isAdmin(me),
    canManageTeams: isAdmin(me),
    canInviteUsers: isAdmin(me) || isLeadOfAnyTeam(me),
    canViewUserAdmin: isAdmin(me) || isLeadOfAnyTeam(me),
  };
}
