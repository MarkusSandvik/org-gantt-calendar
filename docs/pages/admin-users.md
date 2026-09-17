# Admin > Users

**Route:** `/:projectSlug/admin/users`
**Frontend:** `frontend/src/pages/admin/{UsersAdmin,InviteUserModal}.tsx`
**Backend:** `GET /users/admin`, `POST /users/:id/{deactivate,reactivate}`, `PUT/DELETE /users/:id/team-memberships`, `PATCH /users/:id/global-role`, `GET/POST /invitations`, `POST /invitations/:id/revoke`

## Purpose

User accounts, global roles, team membership, and invitations — the RBAC
control surface for the whole deployment (roles here are **global**, not
per-project; see `AUTHORIZATION.md`/`RBAC_PLAN.md`).

## Visibility — scoped very differently by role
This page is not just "read-only vs. editable" like most Admin pages — an
**Admin** sees every user in the organization and their full detail; a
**team Lead** sees only the plain **members** of the one team they lead
(not other Leads, not members of other teams); anyone else gets a 403
from the backend (`GET /users/admin`) and cannot open this page at all.

## Crucial functionality

### User table (Admin view)
Name, email, account status, global role (editable inline via a dropdown
for anyone except yourself), team memberships (each as a removable chip,
plus an inline "+ Add team" control to assign a new team/role pair), last
login, created date, and a Deactivate/Reactivate button (also disabled for
your own account — you can't deactivate yourself).

### Team membership editing
Directly from this table (Admin only): add a user to any team with a role
(Member/Lead) via `PUT /users/:id/team-memberships`, or remove one via the
chip's `×` (`DELETE /users/:id/team-memberships/:teamId`). A user can
belong to multiple teams simultaneously.

### Inviting a user
- **As an Admin**: full control — set the target global role (`User` or
  `Admin`); if `User`, also pick a team and whether they join as Member or
  Lead. An Admin invite has no team.
- **As a team Lead**: a stripped-down form — you can only invite a new
  **Member** into **your own** led team; there's no role or team picker,
  just name and email, because the modal already knows and locks in the
  only choice available to you.
- The created invitation returns a link. In local development (no email
  configured) it's surfaced directly in the UI as "Local-dev link"; in a
  real deployment this would be emailed instead.

### Pending Invitations
A separate table of not-yet-accepted invitations (name, email, team,
target role, who invited them, expiry), each revocable
(`POST /invitations/:id/revoke`).

## Notes
- Deactivating a user blocks login but does not delete their history —
  their name still appears on everything they previously owned, authored,
  or were assigned to.
- See [`authentication.md`](./authentication.md) for what happens on the
  invitee's side of an invitation link.
