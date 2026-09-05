import { useState } from "react";
import type { GlobalRole, Me, Team, TeamRole } from "../../api/types";

interface InviteUserModalProps {
  me: Me;
  teams: Team[];
  submitting: boolean;
  errorMessage: string | null;
  onClose: () => void;
  onSubmit: (payload: {
    email: string;
    name: string;
    team_id: number | null;
    target_global_role: GlobalRole;
    target_team_role: TeamRole | null;
  }) => void;
}

export function InviteUserModal({
  me,
  teams,
  submitting,
  errorMessage,
  onClose,
  onSubmit,
}: InviteUserModalProps) {
  const isAdmin = me.global_role === "admin";
  const ledTeam = teams.find((t) =>
    me.team_memberships.some((m) => m.team_id === t.id && m.team_role === "lead"),
  );

  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [teamId, setTeamId] = useState<number | "">(isAdmin ? "" : (ledTeam?.id ?? ""));
  const [globalRole, setGlobalRole] = useState<GlobalRole>("user");
  const [teamRole, setTeamRole] = useState<TeamRole>("member");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isAdmin) {
      onSubmit({
        email,
        name,
        team_id: ledTeam?.id ?? null,
        target_global_role: "user",
        target_team_role: "member",
      });
      return;
    }
    onSubmit({
      email,
      name,
      team_id: globalRole === "admin" ? null : teamId === "" ? null : Number(teamId),
      target_global_role: globalRole,
      target_team_role: globalRole === "admin" ? null : teamRole,
    });
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Invite a user</h2>
        <form onSubmit={handleSubmit}>
          <label>
            Name
            <input required value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            Email
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          {isAdmin ? (
            <>
              <label>
                Role
                <select
                  value={globalRole}
                  onChange={(e) => setGlobalRole(e.target.value as GlobalRole)}
                >
                  <option value="user">Member or Lead (choose team role below)</option>
                  <option value="admin">Admin</option>
                </select>
              </label>
              {globalRole === "user" && (
                <div className="form-row">
                  <label>
                    Team
                    <select
                      required
                      value={teamId}
                      onChange={(e) => setTeamId(Number(e.target.value))}
                    >
                      <option value="" disabled>
                        Select a team
                      </option>
                      {teams.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Team role
                    <select
                      value={teamRole}
                      onChange={(e) => setTeamRole(e.target.value as TeamRole)}
                    >
                      <option value="member">Member</option>
                      <option value="lead">Lead</option>
                    </select>
                  </label>
                </div>
              )}
            </>
          ) : (
            <p className="form-hint">
              Invited as a Member of {ledTeam?.name ?? "your team"} — Leads can only invite
              Members into their own team.
            </p>
          )}

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <div className="modal-actions">
            <div className="modal-actions__spacer" />
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button button--primary" disabled={submitting}>
              Send invitation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
