# Admin > Teams

**Route:** `/:projectSlug/admin/teams`
**Frontend:** `frontend/src/pages/admin/{TeamsAdmin,TeamFormModal}.tsx`
**Backend:** `GET/POST/PATCH/DELETE /teams`

## Purpose

Manage the teams that every other page's team filters, groupings, and
ownership fields draw from (Gantt row-groups, Calendar's team filter, the
Milestones/Activities "Organization" concept, etc.).

## Crucial functionality

### Team list
Name, category, current Lead (the one member with `team_role: lead`), and
member count. Clicking a row expands an inline member table (name, email,
role) below the list — "Add members from Admin > Users" is where actual
staffing happens; this page doesn't assign people to teams itself.

### Team fields
- **Name**, up to 200 characters.
- **Category** — `Hardware` / `Software` / `Organization`. Purely
  descriptive/organizational; not the same concept as an activity's
  `all_teams` ("Organization") flag.
- **Color** — a color-picker swatch used wherever this specific team needs
  a distinct color (legends, etc.); teams without a custom color fall back
  to the app's generic categorical palette elsewhere.
- **Auto-transfer membership** — when checked, this team's roster
  automatically carries over into any new project created in this
  deployment, rather than starting empty. Intended for standing,
  role-based teams (e.g. "Board", "Admin") that shouldn't need re-staffing
  every season, as opposed to project-specific working teams.

### Deleting a team
A confirm dialog, then a **soft delete** — the team is archived
(`archived_at` set), not hard-deleted, so historical activities/milestones
that reference it keep their team label intact.

## Permissions
- Viewing the list is available to anyone with project access.
- Creating, editing, and deleting all require `canManageTeams` (Admin)
  *and* the project being editable — team leads cannot manage their own
  team's metadata from this page (they can lead/staff it, but not rename,
  recolor, or delete it).
