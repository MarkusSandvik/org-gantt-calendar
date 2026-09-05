import { useState } from "react";
import type {
  Activity,
  ActivityStatus,
  ActivityWritePayload,
  Priority,
  Tag,
  Team,
  User,
} from "../../api/types";
import { ActivityLogPanel } from "../../components/ActivityLogPanel";
import { usePermissions } from "../../hooks/usePermissions";

const STATUS_OPTIONS: ActivityStatus[] = [
  "not_started",
  "in_progress",
  "completed",
  "delayed",
  "blocked",
];

const PRIORITY_OPTIONS: Priority[] = ["low", "normal", "high", "critical"];

interface ActivityFormModalProps {
  projectId: number;
  activity: Activity | null;
  teams: Team[];
  users: User[];
  tags: Tag[];
  hasDependencies?: boolean;
  onSubmit: (payload: ActivityWritePayload) => void;
  onClose: () => void;
  onDelete?: () => void;
  submitting: boolean;
  errorMessage: string | null;
}

function toPayload(projectId: number, activity: Activity | null): ActivityWritePayload {
  if (!activity) {
    return {
      project_id: projectId,
      title: "",
      description: "",
      start_date: "",
      end_date: "",
      status: "not_started",
      progress_percent: 0,
      priority: "normal",
      owner_team_id: null,
      owner_user_id: null,
      contributor_user_ids: [],
      tag_ids: [],
    };
  }
  return {
    project_id: activity.project_id,
    title: activity.title,
    description: activity.description ?? "",
    start_date: activity.start_date,
    end_date: activity.end_date,
    status: activity.status,
    progress_percent: activity.progress_percent,
    priority: activity.priority,
    owner_team_id: activity.owner_team?.id ?? null,
    owner_user_id: activity.owner_user?.id ?? null,
    contributor_user_ids: activity.contributors.map((c) => c.id),
    tag_ids: activity.tags.map((t) => t.id),
  };
}

export function ActivityFormModal({
  projectId,
  activity,
  teams,
  users,
  tags,
  hasDependencies = false,
  onSubmit,
  onClose,
  onDelete,
  submitting,
  errorMessage,
}: ActivityFormModalProps) {
  const [form, setForm] = useState<ActivityWritePayload>(() => toPayload(projectId, activity));
  const [reason, setReason] = useState("");

  const { isAdmin, leadsTeam, canEditActivity, canUpdateAssignedFieldsOnly, canCommentOnActivity } =
    usePermissions();
  // Creating is already gated by the "New Activity" button's own
  // visibility, so full-field editing is assumed here; an existing
  // activity re-checks per-field rights against who owns it.
  const fullEdit = activity ? canEditActivity(activity) : true;
  const assignedOnly = activity ? !fullEdit && canUpdateAssignedFieldsOnly(activity) : false;
  const readOnly = activity != null && !fullEdit && !assignedOnly;
  const canEditLimitedFields = fullEdit || assignedOnly;
  const ownerTeamOptions = activity
    ? teams
    : isAdmin
      ? teams
      : teams.filter((t) => leadsTeam(t.id));

  function toggleContributor(userId: number) {
    setForm((f) => ({
      ...f,
      contributor_user_ids: f.contributor_user_ids.includes(userId)
        ? f.contributor_user_ids.filter((id) => id !== userId)
        : [...f.contributor_user_ids, userId],
    }));
  }

  function toggleTag(tagId: number) {
    setForm((f) => ({
      ...f,
      tag_ids: f.tag_ids.includes(tagId)
        ? f.tag_ids.filter((id) => id !== tagId)
        : [...f.tag_ids, tagId],
    }));
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{activity ? "Edit Activity" : "New Activity"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(reason.trim() ? { ...form, reason: reason.trim() } : form);
          }}
        >
          {readOnly && (
            <p className="form-hint">
              You can view this activity but can't make changes — you're not its owner,
              contributor, or the Lead of {activity?.owner_team?.name ?? "its team"}.
            </p>
          )}
          {assignedOnly && (
            <p className="form-hint">
              You can update status and progress on this activity. Other fields are managed
              by its Lead or an Admin.
            </p>
          )}

          <label>
            Title
            <input
              required
              disabled={!fullEdit}
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
          </label>

          <label>
            Description
            <textarea
              rows={3}
              disabled={!fullEdit}
              value={form.description ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </label>

          <div className="form-row">
            <label>
              Start date
              <input
                type="date"
                required
                disabled={!fullEdit || hasDependencies}
                value={form.start_date}
                onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
              />
            </label>
            <label>
              End date
              <input
                type="date"
                required
                disabled={!fullEdit || hasDependencies}
                value={form.end_date}
                onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
              />
            </label>
          </div>
          {hasDependencies && fullEdit && (
            <p className="form-hint">
              This activity has dependency links, so dates are rescheduled from the Gantt
              (click its bar) to preview the impact on dependent items before applying.
            </p>
          )}

          <div className="form-row">
            <label>
              Status
              <select
                disabled={!canEditLimitedFields}
                value={form.status}
                onChange={(e) =>
                  setForm((f) => ({ ...f, status: e.target.value as ActivityStatus }))
                }
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s.replace("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Priority
              <select
                disabled={!fullEdit}
                value={form.priority}
                onChange={(e) =>
                  setForm((f) => ({ ...f, priority: e.target.value as Priority }))
                }
              >
                {PRIORITY_OPTIONS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Progress %
              <input
                type="number"
                min={0}
                max={100}
                disabled={!canEditLimitedFields}
                value={form.progress_percent}
                onChange={(e) =>
                  setForm((f) => ({ ...f, progress_percent: Number(e.target.value) }))
                }
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              Owner team
              <select
                disabled={!fullEdit}
                value={form.owner_team_id ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    owner_team_id: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              >
                <option value="">None</option>
                {ownerTeamOptions.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Owner
              <select
                disabled={!fullEdit}
                value={form.owner_user_id ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    owner_user_id: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              >
                <option value="">None</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <fieldset disabled={!fullEdit}>
            <legend>Contributors</legend>
            {users.map((u) => (
              <label key={u.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={form.contributor_user_ids.includes(u.id)}
                  onChange={() => toggleContributor(u.id)}
                />
                {u.name}
              </label>
            ))}
          </fieldset>

          <fieldset disabled={!fullEdit}>
            <legend>Tags</legend>
            {tags.map((t) => (
              <label key={t.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={form.tag_ids.includes(t.id)}
                  onChange={() => toggleTag(t.id)}
                />
                {t.name}
              </label>
            ))}
          </fieldset>

          {activity && canEditLimitedFields && (
            <label>
              Reason for this change (optional)
              <input
                placeholder="e.g. Supplier delivery slipped a week"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
          )}

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <div className="modal-actions">
            {activity && onDelete && fullEdit && (
              <button type="button" className="button button--danger" onClick={onDelete}>
                Delete
              </button>
            )}
            <div className="modal-actions__spacer" />
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            {canEditLimitedFields && (
              <button type="submit" className="button button--primary" disabled={submitting}>
                {activity ? "Save changes" : "Create activity"}
              </button>
            )}
          </div>
        </form>

        {activity && (
          <ActivityLogPanel
            entityPath="activities"
            entityAuditType="activity"
            entityId={activity.id}
            teams={teams}
            users={users}
            canComment={canCommentOnActivity(activity)}
          />
        )}
      </div>
    </div>
  );
}
