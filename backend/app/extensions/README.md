# Extensions

This directory is where an organization-specific feature that doesn't belong
in the shared core would live — for example, a hypothetical Vortex
"competition module" that only makes sense for one deployment.

Convention:

- An extension is a normal Python package under this directory
  (`app/extensions/<name>/`).
- It is gated by a flag in the active organization's `features` dict
  (see `app/organizations/<id>/config.py`), never by comparing
  `get_active_organization().id` to a literal string.
- Core code never imports a specific extension by name. If a router,
  service, or scheduled job needs to call into one, it checks the feature
  flag and imports conditionally at that call site — core stays buildable
  and runnable with zero extensions present.
- There is no plugin registry or dynamic loading here. A flag change is a
  redeploy, which is already the unit of change in this single-org-per-
  deployment model — see `ORGANIZATION_PLAN.md`.

This directory is intentionally empty until a real extension is needed.
