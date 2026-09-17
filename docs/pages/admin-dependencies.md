# Admin > Dependencies

**Route:** `/:projectSlug/admin/dependencies`
**Frontend:** `frontend/src/pages/admin/DependenciesAdmin.tsx`
**Backend:** `GET/POST/DELETE /dependencies`

## Purpose

Defines the predecessor → successor links between activities and/or
milestones that drive the Gantt's dependency arrows and the Reschedule
modal's cascade preview (see `gantt.md`) — this is the only place those
links are created or removed.

## Crucial functionality

### Creating a dependency
Two dropdowns (predecessor, successor) each listing every activity and
milestone in the project grouped by type, plus a **lag days** field (an
extra gap enforced between the predecessor finishing and the successor
starting). All dependencies are currently **finish-to-start** — the
successor can't start until the predecessor (plus lag) finishes; there is
no UI for any other dependency type even though the data model has a
`dependency_type` field.

### Server-side validation
- Rejects a dependency where predecessor and successor are the same item.
- Rejects an exact duplicate of an existing dependency (`409`).
- Rejects any dependency that would introduce a **cycle** in the
  schedule graph (`409`) — this is what keeps the Reschedule modal's
  cascade calculation always terminating rather than looping forever.

### Dependency list
Every existing dependency as a row: predecessor label → successor label
(each tagged `milestone` if it is one; unlabeled means activity), lag
days, and a Remove button.

## Permissions
Managing dependencies (the create form and every Remove button) requires
`isAdmin || isLeadOfAnyTeam` *and* the project being editable — everyone
else sees the list read-only with no form. Note this is a project-wide
right, not scoped to "your own team's items" the way some other Lead
permissions are — any Lead can link any two activities/milestones in the
project, regardless of which team owns them.
