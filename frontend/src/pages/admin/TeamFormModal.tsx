import { useState } from "react";
import type { Team, TeamCategory, TeamCreatePayload, TeamUpdatePayload } from "../../api/types";

const CATEGORY_OPTIONS: { value: TeamCategory; label: string }[] = [
  { value: "hardware", label: "Hardware" },
  { value: "software", label: "Software" },
  { value: "organization", label: "Organization" },
];

interface TeamFormModalProps {
  projectId: number;
  team: Team | null;
  onSubmit: (payload: TeamCreatePayload | TeamUpdatePayload) => void;
  onClose: () => void;
  onDelete?: () => void;
  submitting: boolean;
  errorMessage: string | null;
}

export function TeamFormModal({
  projectId,
  team,
  onSubmit,
  onClose,
  onDelete,
  submitting,
  errorMessage,
}: TeamFormModalProps) {
  const [name, setName] = useState(team?.name ?? "");
  const [category, setCategory] = useState<TeamCategory>(team?.category ?? "hardware");
  const [color, setColor] = useState(team?.color ?? "#8a93a1");

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{team ? "Edit Team" : "New Team"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (team) {
              onSubmit({ name, category, color });
            } else {
              onSubmit({ project_id: projectId, name, category, color });
            }
          }}
        >
          <label>
            Name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
            />
          </label>
          <label>
            Category
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as TeamCategory)}
            >
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Color
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)} />
          </label>

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <div className="modal-actions">
            {team && onDelete && (
              <button type="button" className="button button--danger" onClick={onDelete}>
                Delete
              </button>
            )}
            <div className="modal-actions__spacer" />
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button button--primary" disabled={submitting}>
              {team ? "Save changes" : "Create team"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
