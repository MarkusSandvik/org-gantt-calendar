import { useState } from "react";
import type {
  Activity,
  CalendarEvent,
  CalendarEventType,
  CalendarEventWritePayload,
  Team,
  User,
} from "../../api/types";
import { formatISODate } from "../../utils/date";

const EVENT_TYPE_OPTIONS: CalendarEventType[] = [
  "meeting",
  "social",
  "deadline",
  "workshop",
  "recruitment",
  "sponsor",
  "travel",
  "presentation",
  "stand_duty",
  "other",
];

interface CalendarEventModalProps {
  projectId: number;
  event: CalendarEvent | null;
  defaultDate: Date | null;
  teams: Team[];
  users: User[];
  activities: Activity[];
  onSubmit: (payload: CalendarEventWritePayload) => void;
  onClose: () => void;
  onDelete?: () => void;
  submitting: boolean;
  errorMessage: string | null;
}

function toDateTimeLocal(iso: string): string {
  return iso.slice(0, 16);
}

function toPayload(
  projectId: number,
  event: CalendarEvent | null,
  defaultDate: Date | null,
): CalendarEventWritePayload {
  if (!event) {
    const base = formatISODate(defaultDate ?? new Date());
    return {
      project_id: projectId,
      title: "",
      description: null,
      event_type: "meeting",
      start_datetime: `${base}T09:00`,
      end_datetime: `${base}T10:00`,
      all_day: false,
      location: null,
      team_id: null,
      owner_user_id: null,
      related_activity_id: null,
    };
  }
  return {
    project_id: event.project_id,
    title: event.title,
    description: event.description,
    event_type: event.event_type,
    start_datetime: toDateTimeLocal(event.start_datetime),
    end_datetime: toDateTimeLocal(event.end_datetime),
    all_day: event.all_day,
    location: event.location,
    team_id: event.team?.id ?? null,
    owner_user_id: event.owner_user?.id ?? null,
    related_activity_id: event.related_activity?.id ?? null,
  };
}

export function CalendarEventModal({
  projectId,
  event,
  defaultDate,
  teams,
  users,
  activities,
  onSubmit,
  onClose,
  onDelete,
  submitting,
  errorMessage,
}: CalendarEventModalProps) {
  const [form, setForm] = useState<CalendarEventWritePayload>(() =>
    toPayload(projectId, event, defaultDate),
  );

  function toggleAllDay(checked: boolean) {
    setForm((f) => {
      if (checked) {
        const day = f.start_datetime.slice(0, 10);
        return {
          ...f,
          all_day: true,
          start_datetime: `${day}T00:00`,
          end_datetime: `${day}T23:59`,
        };
      }
      return { ...f, all_day: false };
    });
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{event ? "Edit Event" : "New Calendar Event"}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({
              ...form,
              start_datetime:
                form.start_datetime.length === 16 ? `${form.start_datetime}:00` : form.start_datetime,
              end_datetime:
                form.end_datetime.length === 16 ? `${form.end_datetime}:00` : form.end_datetime,
            });
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
              rows={2}
              value={form.description ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value || null }))}
            />
          </label>

          <div className="form-row">
            <label>
              Type
              <select
                value={form.event_type}
                onChange={(e) =>
                  setForm((f) => ({ ...f, event_type: e.target.value as CalendarEventType }))
                }
              >
                {EVENT_TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {t.replace("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="checkbox-label checkbox-label--inline">
              <input
                type="checkbox"
                checked={form.all_day}
                onChange={(e) => toggleAllDay(e.target.checked)}
              />
              All day
            </label>
          </div>

          <div className="form-row">
            <label>
              {form.all_day ? "Start date" : "Start"}
              <input
                type={form.all_day ? "date" : "datetime-local"}
                required
                value={form.all_day ? form.start_datetime.slice(0, 10) : form.start_datetime}
                onChange={(e) => {
                  const value = form.all_day ? `${e.target.value}T00:00` : e.target.value;
                  setForm((f) => ({ ...f, start_datetime: value }));
                }}
              />
            </label>
            <label>
              {form.all_day ? "End date" : "End"}
              <input
                type={form.all_day ? "date" : "datetime-local"}
                required
                value={form.all_day ? form.end_datetime.slice(0, 10) : form.end_datetime}
                onChange={(e) => {
                  const value = form.all_day ? `${e.target.value}T23:59` : e.target.value;
                  setForm((f) => ({ ...f, end_datetime: value }));
                }}
              />
            </label>
          </div>

          <label>
            Location
            <input
              value={form.location ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, location: e.target.value || null }))}
            />
          </label>

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

          <label>
            Related activity
            <select
              value={form.related_activity_id ?? ""}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  related_activity_id: e.target.value ? Number(e.target.value) : null,
                }))
              }
            >
              <option value="">None</option>
              {activities.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title}
                </option>
              ))}
            </select>
          </label>

          {errorMessage && <p className="form-error">{errorMessage}</p>}

          <div className="modal-actions">
            {event && onDelete && (
              <button type="button" className="button button--danger" onClick={onDelete}>
                Delete
              </button>
            )}
            <div className="modal-actions__spacer" />
            <button type="button" className="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button button--primary" disabled={submitting}>
              {event ? "Save changes" : "Create event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
