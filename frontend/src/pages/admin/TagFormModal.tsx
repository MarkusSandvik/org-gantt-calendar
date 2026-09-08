import { useState } from "react";
import type { Tag, TagCreatePayload, TagUpdatePayload } from "../../api/types";

interface TagFormModalProps {
  projectId: number;
  tag: Tag | null;
  onSubmit: (payload: TagCreatePayload | TagUpdatePayload) => void;
  onClose: () => void;
  onDelete?: () => void;
  submitting: boolean;
  errorMessage: string | null;
}

export function TagFormModal({
  projectId,
  tag,
  onSubmit,
  onClose,
  onDelete,
  submitting,
  errorMessage,
}: TagFormModalProps) {
  const [name, setName] = useState(tag?.name ?? "");
  const [color, setColor] = useState(tag?.color ?? "#8a93a1");

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{tag ? "Edit Tag" : "New Tag"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (tag) {
              onSubmit({ name, color });
            } else {
              onSubmit({ project_id: projectId, name, color });
            }
          }}
        >
          <label>
            Name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
            />
          </label>
          <label>
            Color
            <input type="color" value={color} onChange={(e) => setColor(e.target.value)} />
          </label>

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <div className="modal-actions">
            {tag && onDelete && (
              <button type="button" className="button button--danger" onClick={onDelete}>
                Delete
              </button>
            )}
            <div className="modal-actions__spacer" />
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button button--primary" disabled={submitting}>
              {tag ? "Save changes" : "Create tag"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
