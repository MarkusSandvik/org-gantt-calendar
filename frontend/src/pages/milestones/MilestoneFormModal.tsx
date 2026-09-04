import { useState } from "react";
import type {
  Milestone,
  MilestoneStatus,
  MilestoneWritePayload,
  Tag,
  Team,
  User,
} from "../../api/types";

const STATUS_OPTIONS: MilestoneStatus[] = [
  "not_started",
  "on_track",
  "at_risk",
  "completed",
  "missed",
];

interface MilestoneFormModalProps {
  projectId: number;
  milestone: Milestone | null;
  teams: Team[];
  users: User[];
  tags: Tag[];
  hasDependencies?: boolean;
  onSubmit: (payload: MilestoneWritePayload) => void;
  onClose: () => void;
  onDelete?: () => void;
  submitting: boolean;
  errorMessage: string | null;
}

function toPayload(projectId: number, milestone: Milestone | null): MilestoneWritePayload {
  if (!milestone) {
    return {
      project_id: projectId,
      title: "",
      description: "",
      date: "",
      status: "not_started",
      team_id: null,
      owner_user_id: null,
      tag_ids: [],
    };
  }
  return {
    project_id: milestone.project_id,
    title: milestone.title,
    description: milestone.description ?? "",
    date: milestone.date,
    status: milestone.status,
    team_id: milestone.team?.id ?? null,
    owner_user_id: milestone.owner_user?.id ?? null,
    tag_ids: milestone.tags.map((t) => t.id),
  };
}

export function MilestoneFormModal({
  projectId,
  milestone,
  teams,
  users,
  tags,
  hasDependencies = false,
  onSubmit,
  onClose,
  onDelete,
  submitting,
  errorMessage,
}: MilestoneFormModalProps) {
  const [form, setForm] = useState<MilestoneWritePayload>(() =>
    toPayload(projectId, milestone),
  );

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
        <h2>{milestone ? "Edit Milestone" : "New Milestone"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(form);
          }}
        >
          <label>
            Title
            <input
              required
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
          </label>

          <label>
            Description
            <textarea
              rows={3}
              value={form.description ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </label>

          <div className="form-row">
            <label>
              Date
              <input
                type="date"
                required
                disabled={hasDependencies}
                value={form.date}
                onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
              />
            </label>
            <label>
              Status
              <select
                value={form.status}
                onChange={(e) =>
                  setForm((f) => ({ ...f, status: e.target.value as MilestoneStatus }))
                }
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s.replace("_", " ")}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {hasDependencies && (
            <p className="form-hint">
              This milestone has dependency links, so its date is rescheduled from the Gantt
              (click its diamond) to preview the impact on dependent items before applying.
            </p>
          )}

          <div className="form-row">
            <label>
              Team
              <select
                value={form.team_id ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    team_id: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              >
                <option value="">None</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Owner
              <select
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

          <fieldset>
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

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <div className="modal-actions">
            {milestone && onDelete && (
              <button type="button" className="button button--danger" onClick={onDelete}>
                Delete
              </button>
            )}
            <div className="modal-actions__spacer" />
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button button--primary" disabled={submitting}>
              {milestone ? "Save changes" : "Create milestone"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
