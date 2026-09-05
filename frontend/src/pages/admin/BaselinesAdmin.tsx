import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type {
  Baseline,
  BaselineComparison,
  BaselineCreatePayload,
  Project,
} from "../../api/types";
import { usePermissions } from "../../hooks/usePermissions";
import { BaselineFormModal } from "./BaselineFormModal";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function driftClass(deltaDays: number): string {
  if (deltaDays > 0) return "baseline-drift--later";
  if (deltaDays < 0) return "baseline-drift--earlier";
  return "baseline-drift--none";
}

function formatDelta(deltaDays: number): string {
  if (deltaDays === 0) return "On schedule";
  return deltaDays > 0 ? `+${deltaDays}d` : `${deltaDays}d`;
}

export function BaselinesAdmin() {
  const queryClient = useQueryClient();
  const { canManageBaselines } = usePermissions();

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const projectId = projects?.[0]?.id;

  const { data: baselines } = useQuery({
    queryKey: ["baselines", projectId],
    queryFn: () => api.get<Baseline[]>(`/baselines?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const [selectedBaselineId, setSelectedBaselineId] = useState<number | null>(null);
  const { data: comparison } = useQuery({
    queryKey: ["baseline-comparison", selectedBaselineId],
    queryFn: () =>
      api.get<BaselineComparison>(`/baselines/${selectedBaselineId}/comparison`),
    enabled: selectedBaselineId != null,
  });

  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (payload: BaselineCreatePayload) =>
      api.post<Baseline>(`/baselines?project_id=${projectId}`, payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["baselines"] });
      setShowForm(false);
      setFormError(null);
      setSelectedBaselineId(created.id);
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  if (!projectId) {
    return <p>Loading project...</p>;
  }

  return (
    <div>
      <div className="toolbar">
        <p className="page__phase-note">
          A baseline snapshots every activity's and milestone's currently planned dates, so
          you can later compare the original plan against where things actually stand.
        </p>
        {canManageBaselines && (
          <button className="button button--primary" onClick={() => setShowForm(true)}>
            Set Baseline
          </button>
        )}
      </div>

      {baselines && baselines.length === 0 && <p>No baselines yet.</p>}

      {baselines && baselines.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Note</th>
              <th>Created by</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {baselines.map((b) => (
              <tr
                key={b.id}
                onClick={() => setSelectedBaselineId(b.id)}
                className={b.id === selectedBaselineId ? "data-table__row--selected" : ""}
              >
                <td>{b.name}</td>
                <td>{b.note ?? "—"}</td>
                <td>{b.created_by.name}</td>
                <td>{formatDateTime(b.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {comparison && (
        <div className="baseline-comparison">
          <h2>{comparison.baseline.name} — drift vs. current plan</h2>
          {comparison.items.length === 0 && <p>Nothing to compare.</p>}
          {comparison.items.length > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Baseline</th>
                  <th>Current</th>
                  <th>Drift</th>
                </tr>
              </thead>
              <tbody>
                {comparison.items.map((item) => (
                  <tr key={`${item.entity_type}-${item.entity_id}`}>
                    <td>
                      {item.label}{" "}
                      {item.entity_type === "milestone" && (
                        <span className="tag-chip">milestone</span>
                      )}
                    </td>
                    <td>
                      {item.entity_type === "milestone"
                        ? item.baseline_start
                        : `${item.baseline_start} → ${item.baseline_end}`}
                    </td>
                    <td>
                      {item.entity_type === "milestone"
                        ? item.current_start
                        : `${item.current_start} → ${item.current_end}`}
                    </td>
                    <td className={driftClass(item.delta_end_days)}>
                      {formatDelta(item.delta_end_days)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {showForm && (
        <BaselineFormModal
          submitting={createMutation.isPending}
          errorMessage={formError}
          onClose={() => {
            setShowForm(false);
            setFormError(null);
          }}
          onSubmit={(payload) => {
            setFormError(null);
            createMutation.mutate(payload);
          }}
        />
      )}
    </div>
  );
}
