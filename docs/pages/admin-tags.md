# Admin > Tags

**Route:** `/:projectSlug/admin/tags`
**Frontend:** `frontend/src/pages/admin/{TagsAdmin,TagFormModal}.tsx`
**Backend:** `GET/POST/PATCH/DELETE /tags`

## Purpose

The small, project-scoped tag vocabulary applicable to Activities,
Milestones, and Calendar events alike (a single `Tag` model shared across
all three, distinguished by a `TaggableType` — `activity` / `milestone` /
`calendar_event` — on each association, not by separate tag lists).

## Crucial functionality

### Tag list
Name (with its color swatch) and hex color. Nothing else — tags have no
category, description, or other metadata.

### Tag fields
Just **name** (up to 100 characters) and **color** (a color-picker
swatch). Any tag can be applied to any activity, milestone, or calendar
event — there's no restriction tying a tag to one entity type.

### Deleting a tag
A confirm dialog, then a **soft delete** (archived, not hard-deleted) —
existing tag associations on activities/milestones/events keep working
and displaying the tag's name/color even after it's archived here; it
simply stops appearing as an option for *new* tagging.

## Permissions
Creating, editing, and deleting all require `canManageTags` (Admin) and
the project being editable. Everyone else sees the list read-only —
applying an *existing* tag to an item is done from that item's own edit
form (Activity/Milestone/Calendar event), not from this page.
