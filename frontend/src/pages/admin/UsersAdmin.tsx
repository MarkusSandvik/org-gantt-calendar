import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type {
  GlobalRole,
  Invitation,
  InvitationCreatePayload,
  InvitationCreateResponse,
  Team,
  TeamRole,
  UserAdmin,
} from "../../api/types";
import { useCurrentUser } from "../../hooks/useAuth";
import { InviteUserModal } from "./InviteUserModal";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function UsersAdmin() {
  const queryClient = useQueryClient();
  const { me } = useCurrentUser();

  const { data: teams } = useQuery({
    queryKey: ["teams"],
    queryFn: () => api.get<Team[]>("/teams"),
  });
  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ["users-admin"],
    queryFn: () => api.get<UserAdmin[]>("/users/admin"),
  });
  const { data: invitations } = useQuery({
    queryKey: ["invitations"],
    queryFn: () => api.get<Invitation[]>("/invitations"),
  });

  const [showInvite, setShowInvite] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [lastInvite, setLastInvite] = useState<InvitationCreateResponse | null>(null);

  const inviteMutation = useMutation({
    mutationFn: (payload: InvitationCreatePayload) =>
      api.post<InvitationCreateResponse>("/invitations", payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["invitations"] });
      setShowInvite(false);
      setInviteError(null);
      setLastInvite(created);
    },
    onError: (err: ApiError) => setInviteError(err.message),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "deactivate" | "reactivate" }) =>
      api.post<UserAdmin>(`/users/${id}/${action}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users-admin"] }),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => api.post(`/invitations/${id}/revoke`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invitations"] }),
  });

  const membershipMutation = useMutation({
    mutationFn: ({
      userId,
      team_id,
      team_role,
    }: {
      userId: number;
      team_id: number;
      team_role: TeamRole;
    }) => api.put<UserAdmin>(`/users/${userId}/team-memberships`, { team_id, team_role }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users-admin"] }),
  });

  const removeMembershipMutation = useMutation({
    mutationFn: ({ userId, teamId }: { userId: number; teamId: number }) =>
      api.delete(`/users/${userId}/team-memberships/${teamId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users-admin"] }),
  });

  const globalRoleMutation = useMutation({
    mutationFn: ({ userId, global_role }: { userId: number; global_role: GlobalRole }) =>
      api.patch<UserAdmin>(`/users/${userId}/global-role`, { global_role }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users-admin"] }),
  });

  if (!me || usersLoading) {
    return <p>Loading users...</p>;
  }

  const isAdmin = me.global_role === "admin";
  const pendingInvitations = (invitations ?? []).filter((i) => i.status === "pending");

  return (
    <div>
      <div className="toolbar">
        <p className="page__phase-note">
          {isAdmin
            ? "Every user in the organization."
            : "Members of your team."}
        </p>
        <button className="button button--primary" onClick={() => setShowInvite(true)}>
          Invite user
        </button>
      </div>

      {lastInvite?.invite_url && (
        <p className="form-hint">
          Invitation created. Local-dev link (would normally be emailed):{" "}
          <code>{lastInvite.invite_url}</code>
        </p>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Status</th>
            <th>Role</th>
            <th>Teams</th>
            <th>Last login</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(users ?? []).map((user) => (
            <tr key={user.id}>
              <td>{user.name}</td>
              <td>{user.email}</td>
              <td>{user.status}</td>
              <td>
                {isAdmin && user.id !== me.id ? (
                  <select
                    value={user.global_role}
                    onChange={(e) =>
                      globalRoleMutation.mutate({
                        userId: user.id,
                        global_role: e.target.value as GlobalRole,
                      })
                    }
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                ) : (
                  user.global_role
                )}
              </td>
              <td>
                {user.team_memberships.length === 0 && "—"}
                {user.team_memberships.map((m) => (
                  <span key={m.team_id} className="tag-chip">
                    {m.team_name} ({m.team_role})
                    {isAdmin && (
                      <button
                        className="tag-chip__remove"
                        title="Remove from team"
                        onClick={() =>
                          removeMembershipMutation.mutate({ userId: user.id, teamId: m.team_id })
                        }
                      >
                        ×
                      </button>
                    )}
                  </span>
                ))}
                {isAdmin && teams && teams.length > 0 && (
                  <AddMembershipControl
                    teams={teams}
                    onAdd={(team_id, team_role) =>
                      membershipMutation.mutate({ userId: user.id, team_id, team_role })
                    }
                  />
                )}
              </td>
              <td>{formatDate(user.last_login_at)}</td>
              <td>{formatDate(user.created_at)}</td>
              <td>
                {user.id !== me.id && (
                  <button
                    className="button"
                    onClick={() => {
                      const action = user.status === "active" ? "deactivate" : "reactivate";
                      if (
                        action === "deactivate" &&
                        !confirm(`Deactivate ${user.name}? They will no longer be able to log in.`)
                      ) {
                        return;
                      }
                      statusMutation.mutate({ id: user.id, action });
                    }}
                  >
                    {user.status === "active" ? "Deactivate" : "Reactivate"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Pending Invitations</h2>
      {pendingInvitations.length === 0 && <p>No pending invitations.</p>}
      {pendingInvitations.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Team</th>
              <th>Role</th>
              <th>Invited by</th>
              <th>Expires</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pendingInvitations.map((invitation) => (
              <tr key={invitation.id}>
                <td>{invitation.name}</td>
                <td>{invitation.email}</td>
                <td>{invitation.team?.name ?? "—"}</td>
                <td>
                  {invitation.target_global_role === "admin"
                    ? "Admin"
                    : invitation.target_team_role}
                </td>
                <td>{invitation.invited_by.name}</td>
                <td>{formatDate(invitation.expires_at)}</td>
                <td>
                  <button
                    className="button"
                    onClick={() => revokeMutation.mutate(invitation.id)}
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showInvite && (
        <InviteUserModal
          me={me}
          teams={teams ?? []}
          submitting={inviteMutation.isPending}
          errorMessage={inviteError}
          onClose={() => {
            setShowInvite(false);
            setInviteError(null);
          }}
          onSubmit={(payload) => {
            setInviteError(null);
            inviteMutation.mutate(payload);
          }}
        />
      )}
    </div>
  );
}

function AddMembershipControl({
  teams,
  onAdd,
}: {
  teams: Team[];
  onAdd: (teamId: number, teamRole: TeamRole) => void;
}) {
  const [open, setOpen] = useState(false);
  const [teamId, setTeamId] = useState<number | "">("");
  const [teamRole, setTeamRole] = useState<TeamRole>("member");

  if (!open) {
    return (
      <button className="tag-chip tag-chip--add" onClick={() => setOpen(true)}>
        + Add team
      </button>
    );
  }

  return (
    <div className="add-membership-control">
      <select value={teamId} onChange={(e) => setTeamId(Number(e.target.value))}>
        <option value="" disabled>
          Team
        </option>
        {teams.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
      <select value={teamRole} onChange={(e) => setTeamRole(e.target.value as TeamRole)}>
        <option value="member">Member</option>
        <option value="lead">Lead</option>
      </select>
      <button
        className="button button--primary"
        disabled={teamId === ""}
        onClick={() => {
          if (teamId !== "") {
            onAdd(Number(teamId), teamRole);
            setOpen(false);
            setTeamId("");
          }
        }}
      >
        Add
      </button>
      <button className="button" onClick={() => setOpen(false)}>
        Cancel
      </button>
    </div>
  );
}
