import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { AuditLogEntry, Comment, CommentWritePayload, Team, User } from "../api/types";

type EntityPath = "activities" | "milestones";

interface ActivityLogPanelProps {
  entityPath: EntityPath;
  entityAuditType: "activity" | "milestone";
  entityId: number;
  teams?: Team[];
  users?: User[];
  canComment?: boolean;
}

type TimelineEntry =
  | { kind: "comment"; timestamp: string; comment: Comment }
  | { kind: "audit"; timestamp: string; entry: AuditLogEntry };

const FIELD_LABELS: Record<string, string> = {
  title: "title",
  description: "description",
  start_date: "start date",
  end_date: "end date",
  date: "date",
  progress_percent: "progress",
  priority: "priority",
  owner_team_id: "owner team",
  owner_user_id: "owner",
  team_id: "team",
};

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ActivityLogPanel({
  entityPath,
  entityAuditType,
  entityId,
  teams,
  users,
  canComment = true,
}: ActivityLogPanelProps) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");

  const { data: comments } = useQuery({
    queryKey: [entityPath, entityId, "comments"],
    queryFn: () => api.get<Comment[]>(`/${entityPath}/${entityId}/comments`),
  });
  const { data: auditEntries } = useQuery({
    queryKey: ["audit-log", entityAuditType, entityId],
    queryFn: () =>
      api.get<AuditLogEntry[]>(
        `/audit-log?entity_type=${entityAuditType}&entity_id=${entityId}`,
      ),
  });

  const addCommentMutation = useMutation({
    mutationFn: (payload: CommentWritePayload) =>
      api.post<Comment>(`/${entityPath}/${entityId}/comments`, payload),
    onSuccess: () => {
      setNote("");
      queryClient.invalidateQueries({ queryKey: [entityPath, entityId, "comments"] });
    },
  });

  function resolveValue(fieldName: string, raw: string | null): string {
    if (raw === null) return "—";
    if (fieldName === "owner_team_id" || fieldName === "team_id") {
      return teams?.find((t) => String(t.id) === raw)?.name ?? raw;
    }
    if (fieldName === "owner_user_id") {
      return users?.find((u) => String(u.id) === raw)?.name ?? raw;
    }
    return raw;
  }

  const timeline: TimelineEntry[] = [
    ...(comments ?? []).map((c) => ({
      kind: "comment" as const,
      timestamp: c.created_at,
      comment: c,
    })),
    ...(auditEntries ?? []).map((e) => ({
      kind: "audit" as const,
      timestamp: e.timestamp,
      entry: e,
    })),
  ].sort((a, b) => a.timestamp.localeCompare(b.timestamp));

  return (
    <div className="activity-log">
      <h3>Activity Log</h3>
      {timeline.length === 0 && <p className="activity-log__empty">No activity yet.</p>}
      <ul className="activity-log__list">
        {timeline.map((item) =>
          item.kind === "comment" ? (
            <li key={`c-${item.comment.id}`} className="activity-log__entry">
              <div className="activity-log__meta">
                <strong>{item.comment.author.name}</strong>
                <span>{formatTimestamp(item.comment.created_at)}</span>
              </div>
              {item.comment.status_change_from && (
                <div className="activity-log__status-change">
                  Status changed: {item.comment.status_change_from.replace("_", " ")} →{" "}
                  {item.comment.status_change_to?.replace("_", " ")}
                </div>
              )}
              {item.comment.body && <p>{item.comment.body}</p>}
            </li>
          ) : (
            <li
              key={`a-${item.entry.id}`}
              className="activity-log__entry activity-log__entry--audit"
            >
              <div className="activity-log__meta">
                <strong>{item.entry.user.name}</strong>
                <span>{formatTimestamp(item.entry.timestamp)}</span>
              </div>
              <p>
                Changed {FIELD_LABELS[item.entry.field_name] ?? item.entry.field_name}:{" "}
                <span className="activity-log__value">
                  {resolveValue(item.entry.field_name, item.entry.old_value)}
                </span>{" "}
                →{" "}
                <span className="activity-log__value">
                  {resolveValue(item.entry.field_name, item.entry.new_value)}
                </span>
              </p>
              {item.entry.reason && (
                <p className="activity-log__reason">Reason: {item.entry.reason}</p>
              )}
            </li>
          ),
        )}
      </ul>

      {canComment && (
        <div className="activity-log__add">
          <textarea
            rows={2}
            placeholder="Add a note..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button
            type="button"
            className="button"
            disabled={!note.trim() || addCommentMutation.isPending}
            onClick={() => addCommentMutation.mutate({ body: note.trim() })}
          >
            Add note
          </button>
        </div>
      )}
    </div>
  );
}
