# Organization Abstraction — Migration Plan

Approved architecture for turning this from "the Vortex app" into a reusable
project-control platform that any organization can deploy, without forking
or duplicating the codebase. This document is the durable record of the
assessment; implementation proceeds phase by phase against it.

## Findings (before refactoring)

A full grep of the tree found the organization-specific surface area is
**almost entirely confined to one file**: `backend/app/db/seed.py` (team
names, tag names, project name/description, demo users/activities). Beyond
that: two literal "Org Planner" strings in the frontend, no logo/favicon
(still Vite defaults), and no theme system at all (no dark mode, no
`data-theme`, one flat `:root` token set). No `Organization` database
concept exists; `Project` already scopes `Team`/`Tag`/`Activity`/
`Milestone`/`CalendarEvent`/`Baseline` via `project_id`.

Critically: **no business logic anywhere compares a team or tag by name.**
`app/core/permissions.py` (built during the RBAC work) already resolves
everything through `TeamMembership.team_id`. This refactor is materially
smaller than it would be in a codebase that hadn't already adopted that
discipline.

## Decisions

- **No `Organization` database entity, for now.** Every table that would
  need `organization_id` has none today, and adding it means migrating
  nearly every table for a value that would be constant on every row in a
  single-org-per-deployment model. `Project` already provides the scoping
  boundary in practice. Revisit only if true multi-tenancy (one running
  server, several orgs' data coexisting) becomes a real requirement — not
  before.
- **Org identity is a deployment-time config selection, not runtime state.**
  `APP_ORGANIZATION` (backend) / `VITE_ORGANIZATION` (frontend) pick a
  profile once, at process start / build time. Both default to `"default"`
  when unset, so local dev needs zero configuration, exactly as today.
- **One repository, one `master` branch, no per-org branches or forks.**
  `organizations/<id>/` and `branding/profiles/<id>.ts` live side by side in
  the same repo. Deploying a second org = same repo, different env vars,
  different database. Shared-core fixes are automatically available to
  every deployment because there is only one codebase. Git tags
  (`v0.5.0`, ...) mark stable points a deployment can pin to; no package
  registry or publish step.
- **No terminology/i18n layer.** "Team", "Lead", "Activity" stay plain
  English UI copy. Only the two brand-name literals and the CSV import
  template's example row get centralized. Revisit only if a real second
  org needs different words — not speculatively.
- **Theme retrofit uses the lightweight approach**: extend the *existing*
  `--color-*` token names in place with a `@media (prefers-color-scheme:
  dark)` block and `[data-theme]` override blocks, rather than introducing
  a new semantic token layer. Every existing component already reads these
  variables, so dark mode falls out with no component-level CSS changes;
  the only real work is converting the handful of stray hardcoded hex
  colors into variables.
- **Feature flags are a static, typed config object** (`features: {...}`
  in each org's profile), not a database table or plugin registry. A flag
  change is a redeploy, which is already the unit of change in this model.

## Target structure

```text
backend/
  app/
    core/
      organization.py       OrganizationConfig model + get_active_organization()
    organizations/
      default/config.py     neutral profile: "Example Organization"
      vortex/config.py      real org profile
    extensions/              empty; convention documented in extensions/README.md
    db/seed.py               reads the active profile instead of inline constants
frontend/
  src/
    branding/
      types.ts               BrandingConfig type
      index.ts                picks the active profile from VITE_ORGANIZATION
      profiles/{default,vortex}.ts
    extensions/               empty; same convention as backend
```

## Configuration strategy

| Lives in | What |
|---|---|
| Database (unchanged) | Teams, Tags, Projects, Users — instance data, edited via the Admin UI you already have |
| Static org profile (new) | Display name, product name, logo/favicon paths, default theme, seed-only team/tag lists, feature flags |
| Environment variables | `APP_ORGANIZATION` / `VITE_ORGANIZATION` (which profile), plus the existing secrets/DB-URL/session settings |

## Implementation phases

1. Config abstraction scaffolding (backend `organizations/`, frontend `branding/`).
2. Move seed data into org profiles; `seed.py` becomes profile-driven.
3. Frontend branding wiring (brand name, favicon/logo).
4. Backend cleanup of remaining literals (CSV template example row).
5. Organization DB entity — **skipped by decision above**, documented only.
6. Default/neutral organization profile, verified sufficient to boot alone.
7. Feature flag / extension boundary (empty `extensions/` + convention doc).
8. Theme retrofit (light/dark/system), lightweight approach.
9. Tests (config loading, no-name-based-permissions assertion, default org boots).
10. Documentation (this file, README architecture + "add an organization" guide, `.env.example` updates).
11. Final verification: both `default` and `vortex` profiles boot correctly; full test suite green.

## Acceptance criteria (from the original request)

Core has no Vortex-specific assumptions · teams/tags are data · branding is
replaceable without editing core components · themes stay generic ·
authorization never depends on team names · a neutral org can run the app ·
Vortex config can be added without forking core · extensions have a clean
boundary · shared fixes reach every deployment automatically · existing
functionality and data are preserved · the repo documents how to add
another organization.
