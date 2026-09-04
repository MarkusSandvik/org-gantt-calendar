import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type {
  SchedulableType,
  ScheduleChangeItem,
  SchedulingApplyResponse,
  SchedulingChangeRequest,
} from "../../api/types";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

interface RescheduleModalProps {
  entityType: SchedulableType;
  entityId: number;
  label: string;
  initialStartDate: string;
  initialEndDate: string;
  onClose: () => void;
}

export function RescheduleModal({
  entityType,
  entityId,
  label,
  initialStartDate,
  initialEndDate,
  onClose,
}: RescheduleModalProps) {
  const queryClient = useQueryClient();
  const isMilestone = entityType === "milestone";

  const [startDate, setStartDate] = useState(initialStartDate);
  const [endDate, setEndDate] = useState(initialEndDate);
  const [appliedGroupId, setAppliedGroupId] = useState<string | null>(null);
  const [undone, setUndone] = useState(false);

  const debouncedStart = useDebouncedValue(startDate, 300);
  const debouncedEnd = useDebouncedValue(endDate, 300);

  const hasChanged = debouncedStart !== initialStartDate || debouncedEnd !== initialEndDate;
  const datesValid = debouncedEnd >= debouncedStart;

  const previewQuery = useQuery({
    queryKey: ["scheduling-preview", entityType, entityId, debouncedStart, debouncedEnd],
    queryFn: () =>
      api.post<ScheduleChangeItem[]>("/scheduling/preview", {
        entity_type: entityType,
        entity_id: entityId,
        new_start_date: debouncedStart,
        new_end_date: debouncedEnd,
      } satisfies SchedulingChangeRequest),
    enabled: hasChanged && datesValid && appliedGroupId == null,
  });

  const applyMutation = useMutation({
    mutationFn: () =>
      api.post<SchedulingApplyResponse>("/scheduling/apply", {
        entity_type: entityType,
        entity_id: entityId,
        new_start_date: debouncedStart,
        new_end_date: debouncedEnd,
      } satisfies SchedulingChangeRequest),
    onSuccess: (data) => {
      setAppliedGroupId(data.change_group_id);
      queryClient.invalidateQueries({ queryKey: ["activities"] });
      queryClient.invalidateQueries({ queryKey: ["milestones"] });
    },
  });

  const undoMutation = useMutation({
    mutationFn: () =>
      api.post<ScheduleChangeItem[]>("/scheduling/undo", {
        change_group_id: appliedGroupId,
      }),
    onSuccess: () => {
      setUndone(true);
      queryClient.invalidateQueries({ queryKey: ["activities"] });
      queryClient.invalidateQueries({ queryKey: ["milestones"] });
    },
  });

  const otherChanges = (previewQuery.data ?? []).filter(
    (c) => !(c.entity_type === entityType && c.entity_id === entityId),
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Reschedule "{label}"</h2>

        {appliedGroupId && !undone && (
          <p className="reschedule-applied">
            Schedule updated.{" "}
            <button
              type="button"
              className="button"
              onClick={() => undoMutation.mutate()}
              disabled={undoMutation.isPending}
            >
              Undo
            </button>
          </p>
        )}
        {undone && <p className="reschedule-applied">Change undone.</p>}

        {!appliedGroupId && (
          <>
            <div className="form-row">
              <label>
                {isMilestone ? "Date" : "Start date"}
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => {
                    setStartDate(e.target.value);
                    if (isMilestone) setEndDate(e.target.value);
                  }}
                />
              </label>
              {!isMilestone && (
                <label>
                  End date
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </label>
              )}
            </div>

            {!datesValid && (
              <p className="form-error">End date must not be before start date.</p>
            )}

            {hasChanged && datesValid && (
              <div className="reschedule-impact">
                {previewQuery.isFetching && <p>Checking impact...</p>}
                {previewQuery.isError && (
                  <p className="form-error">{(previewQuery.error as ApiError).message}</p>
                )}
                {previewQuery.data && otherChanges.length === 0 && (
                  <p>No other activities or milestones are affected.</p>
                )}
                {previewQuery.data && otherChanges.length > 0 && (
                  <>
                    <p>
                      This change affects {otherChanges.length} other item
                      {otherChanges.length === 1 ? "" : "s"}:
                    </p>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Item</th>
                          <th>From</th>
                          <th>To</th>
                          <th>Shift</th>
                        </tr>
                      </thead>
                      <tbody>
                        {otherChanges.map((c) => (
                          <tr key={`${c.entity_type}-${c.entity_id}`}>
                            <td>
                              {c.label}{" "}
                              {c.entity_type === "milestone" && (
                                <span className="tag-chip">milestone</span>
                              )}
                            </td>
                            <td>
                              {c.old_start_date} → {c.old_end_date}
                            </td>
                            <td>
                              {c.new_start_date} → {c.new_end_date}
                            </td>
                            <td>+{c.delta_days}d</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </>
                )}
              </div>
            )}

            {applyMutation.isError && (
              <p className="form-error">{(applyMutation.error as ApiError).message}</p>
            )}

            <div className="modal-actions">
              <div className="modal-actions__spacer" />
              <button type="button" className="button" onClick={onClose}>
                Cancel
              </button>
              <button
                type="button"
                className="button button--primary"
                disabled={!hasChanged || !datesValid || applyMutation.isPending}
                onClick={() => applyMutation.mutate()}
              >
                Apply changes
              </button>
            </div>
          </>
        )}

        {appliedGroupId && (
          <div className="modal-actions">
            <div className="modal-actions__spacer" />
            <button type="button" className="button button--primary" onClick={onClose}>
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
