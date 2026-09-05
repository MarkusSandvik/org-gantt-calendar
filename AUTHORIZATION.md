# Authorization

The live permission matrix for Org Gantt & Calendar's Admin/Lead/Member
model. All checks are implemented in `backend/app/core/permissions.py` and
enforced server-side — the frontend's UI adapts to these (Phase 9) but never
gates anything on its own; see `RBAC_PLAN.md` for the full architecture
writeup and phase history.

## Roles

- **Admin** (`User.global_role == ADMIN`) — unrestricted, organization-wide.
- **Lead** (`TeamMembership.team_role == LEAD`) — organization-wide *view*,
  full management authority within the one team they lead. A user leads at
  most one team.
- **Member** — everyone else. Organization-wide *view*; may update
  `status`/`progress_percent` and comment only on activities/milestones
  they are assigned to as owner or contributor.

## Permission matrix

| Resource | Action | Member | Lead (own group) | Lead (other group) | Admin |
|---|---|---|---|---|---|
| Activity | View | Yes | Yes | Yes | Yes |
| Activity | Create | No | Yes | No | Yes |
| Activity | Edit progress/status | Assigned only | Yes | No | Yes |
| Activity | Edit schedule/priority/owner/contributors/team | No | Yes | No | Yes |
| Activity | Delete | No | Yes | No | Yes |
| Comment | Create (on activity/milestone) | Assigned only | Yes (own group) | No | Yes |
| Milestone | View | Yes | Yes | Yes | Yes |
| Milestone | Manage (has a team) | No | Yes (matching team) | No | Yes |
| Milestone | Manage (org-wide, no team) | No | No | No | Yes |
| Dependency | View | Yes | Yes | Yes | Yes |
| Dependency | Create/delete, at least one endpoint in own team | No | Yes | No | Yes |
| Dependency | Create/delete touching only other teams | No | No | No | Yes |
| CalendarEvent | Manage (has a team) | No | Yes (matching team) | No | Yes |
| CalendarEvent | Manage (org-wide, no team) | No | No | No | Yes |
| Scheduling | Preview | No | Yes (own group) | No | Yes |
| Scheduling | Apply — impact stays in own team | No | Yes | No | Yes |
| Scheduling | Apply — impact reaches another team/global milestone | No | Blocked (409 + impact report) | No | Yes |
| Baseline | Manage | No | No | No | Yes |
| Team | Manage | No | No | No | Yes |
| Settings | Manage | No | No | No | Yes |
| User | Invite Member | No | Yes (own group only) | — | Yes |
| User | Invite Lead | No | No | No | Yes |
| User | Invite Admin | No | No | No | Yes |
| User | Change global role / promote / demote | No | No | No | Yes |
| User | Move between teams | No | No | No | Yes |
| User | Deactivate | No | Own-group Members only | No | Yes |

**Tags** currently have no mutation endpoints at all (read-only since Phase
2 of the base app) — there is nothing to authorize yet; `Tag` also has no
`team_id`, so "Lead manages own group's tags" from the original request
isn't wired to anything real. Flagged here rather than left silent.

## Implementation

- `app/core/permissions.py::require(condition, detail=...)` — raises a 403
  `PermissionDenied` when `condition` is false. Every mutating endpoint
  calls one of the named `can_*` resolvers as that condition.
- Each resolver takes the acting `User`, the `Session`, and the resource
  (or the specific fields being changed, for activities) — never a bare
  role string — so the check is always against the real row in the
  database, not a claim in the request payload.
- `is_admin(user)` short-circuits every resolver to `True` first.
- `get_led_team_id(db, user)` / `leads_team(db, user, team_id)` are the
  only places "is this user the Lead of this team" is computed — a single
  source of truth for that check.
- Cross-team scheduling impact (Section 7 of `RBAC_PLAN.md`) is enforced in
  `services/scheduling.py`, not `permissions.py`, since it needs the
  computed propagation result, not just the request's own resource.
