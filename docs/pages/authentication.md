# Authentication (Login, Invitations, Password Reset)

**Routes:** `/login`, `/accept-invitation?token=`, `/reset-password?token=`
**Frontend:** `frontend/src/pages/{Login,AcceptInvitation,ResetPassword}.tsx`
**Backend:** `POST /auth/login`, `POST /auth/password-reset/{request,confirm}`, `GET /invitations/preview/:token`, `POST /invitations/accept`

## Purpose

The three unauthenticated entry points into the app — none of these routes
require a session, and all three redirect into the app (`/`) on success.

## Login (`/login`)

- Email + password form. On success, navigates to `/` (which redirects
  into the user's default project).
- Renders the active organization's branding: logo (falls back to a plain
  product-name heading if the org has no `logoHref`), tagline, and a link
  to `websiteUrl` if configured — this is the one page in the app where
  branding is most visible.
- **Forgot your password?** expands an inline form (same card, no
  navigation) that posts an email to `/auth/password-reset/request`. The
  response is always the same generic confirmation regardless of whether
  the email exists, to avoid leaking which emails are registered. In local
  development, the actual reset link is only printed to the backend
  server's console (there is no email sending configured — see
  `docs`/`CHANGELOG.md` for why email integration is deferred).

## Reset Password (`/reset-password?token=`)

- Requires a `token` query param (from the emailed/console-logged reset
  link); without one it shows a plain error instead of a form.
- A single new-password field (minimum 8 characters) submitted to
  `/auth/password-reset/confirm`. On success, shows a confirmation and a
  button back to `/login` — it does **not** log the user in automatically.

## Accept Invitation (`/accept-invitation?token=`)

- Requires a `token` query param. Loads an invitation preview
  (`GET /invitations/preview/:token`) showing who the invite is for, which
  team (if any), what team role (`Member`/`Lead`), and whether it grants
  Admin — all read-only context so the invitee knows what they're accepting
  before setting a password.
- An expired or invalid token shows "This invitation link is invalid or
  has expired." instead of a form.
- Setting a password (minimum 8 characters) and submitting calls
  `POST /invitations/accept`, which both creates/activates the user
  **and** logs them in immediately (the response `Me` object is written
  directly into the query cache), then navigates to `/` — unlike password
  reset, this flow ends already authenticated.

## Notes
- All three pages share the same `.auth-card` layout/styling.
- None of these pages are reachable once a session exists — `RequireAuth`
  gates every other route, but these three are deliberately outside it.
