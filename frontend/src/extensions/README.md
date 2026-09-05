# Extensions

This directory is where an organization-specific UI feature that doesn't
belong in the shared core would live — for example, a hypothetical Vortex
"competition module" page that only makes sense for one deployment.

Convention:

- An extension is a normal folder under this directory
  (`src/extensions/<name>/`).
- It is gated by a flag in the active branding profile's `features` dict
  (see `src/branding/profiles/<id>.ts`), never by comparing
  `branding.id` to a literal string.
- Core components never import a specific extension by name. A route or
  nav item that needs one checks the feature flag and imports it
  conditionally at that point — core stays buildable and runnable with
  zero extensions present.
- There is no plugin registry here. A flag change is a redeploy, which is
  already the unit of change in this single-org-per-deployment model —
  see `ORGANIZATION_PLAN.md`.

This directory is intentionally empty until a real extension is needed.
