import { useState } from "react";
import type { BaselineCreatePayload } from "../../api/types";

interface BaselineFormModalProps {
  onSubmit: (payload: BaselineCreatePayload) => void;
  onClose: () => void;
  submitting: boolean;
  errorMessage: string | null;
}

const DEFAULT_NAME = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
}).format(new Date());

export function BaselineFormModal({
  onSubmit,
  onClose,
  submitting,
  errorMessage,
}: BaselineFormModalProps) {
  const [name, setName] = useState(`Baseline — ${DEFAULT_NAME}`);
  const [note, setNote] = useState("");

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Set Baseline</h2>
        <p className="page__phase-note">
          Snapshots every activity's and milestone's currently planned dates. Existing
          baselines are never overwritten.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ name, note: note.trim() || null });
          }}
        >
          <label>
            Name
            <input required value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            Note (optional)
            <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          </label>

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <div className="modal-actions">
            <div className="modal-actions__spacer" />
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button button--primary" disabled={submitting}>
              Set baseline
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
