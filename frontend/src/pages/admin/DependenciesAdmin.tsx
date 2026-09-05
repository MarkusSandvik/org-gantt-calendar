import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import { usePermissions } from "../../hooks/usePermissions";
import type {
  Activity,
  Dependency,
  DependencyWritePayload,
  Milestone,
  Project,
  SchedulableType,
} from "../../api/types";

interface EndpointOption {
  type: SchedulableType;
  id: number;
  label: string;
}

function encodeOption(type: SchedulableType, id: number): string {
  return `${type}:${id}`;
}

function decodeOption(value: string): { type: SchedulableType; id: number } | null {
  const [type, idStr] = value.split(":");
  if (!type || !idStr) return null;
  return { type: type as SchedulableType, id: Number(idStr) };
}

export function DependenciesAdmin() {
  const queryClient = useQueryClient();
  const { isAdmin, isLeadOfAnyTeam } = usePermissions();
  const canManageDependencies = isAdmin || isLeadOfAnyTeam;

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const projectId = projects?.[0]?.id;

  const { data: activities } = useQuery({
    queryKey: ["activities", "all", { projectId }],
    queryFn: () => api.get<Activity[]>(`/activities?project_id=${projectId}`),
    enabled: projectId != null,
  });
  const { data: milestones } = useQuery({
    queryKey: ["milestones", "all", { projectId }],
    queryFn: () => api.get<Milestone[]>(`/milestones?project_id=${projectId}`),
    enabled: projectId != null,
  });
  const { data: dependencies } = useQuery({
    queryKey: ["dependencies"],
    queryFn: () => api.get<Dependency[]>("/dependencies"),
  });

  const options: EndpointOption[] = [
    ...(activities ?? []).map((a) => ({ type: "activity" as const, id: a.id, label: a.title })),
    ...(milestones ?? []).map((m) => ({
      type: "milestone" as const,
      id: m.id,
      label: m.title,
    })),
  ];

  const [predecessor, setPredecessor] = useState("");
  const [successor, setSuccessor] = useState("");
  const [lagDays, setLagDays] = useState(0);
  const [formError, setFormError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (payload: DependencyWritePayload) =>
      api.post<Dependency>("/dependencies", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dependencies"] });
      setPredecessor("");
      setSuccessor("");
      setLagDays(0);
      setFormError(null);
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/dependencies/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dependencies"] }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const pred = decodeOption(predecessor);
    const succ = decodeOption(successor);
    if (!pred || !succ) {
      setFormError("Choose both a predecessor and a successor.");
      return;
    }
    createMutation.mutate({
      predecessor_type: pred.type,
      predecessor_id: pred.id,
      successor_type: succ.type,
      successor_id: succ.id,
      dependency_type: "finish_to_start",
      lag_days: lagDays,
    });
  }

  return (
    <div>
      {canManageDependencies && (
      <form className="dependency-form" onSubmit={handleSubmit}>
        <select value={predecessor} onChange={(e) => setPredecessor(e.target.value)} required>
          <option value="">Predecessor...</option>
          <optgroup label="Activities">
            {options
              .filter((o) => o.type === "activity")
              .map((o) => (
                <option key={encodeOption(o.type, o.id)} value={encodeOption(o.type, o.id)}>
                  {o.label}
                </option>
              ))}
          </optgroup>
          <optgroup label="Milestones">
            {options
              .filter((o) => o.type === "milestone")
              .map((o) => (
                <option key={encodeOption(o.type, o.id)} value={encodeOption(o.type, o.id)}>
                  {o.label}
                </option>
              ))}
          </optgroup>
        </select>
        <span className="dependency-form__arrow">→</span>
        <select value={successor} onChange={(e) => setSuccessor(e.target.value)} required>
          <option value="">Successor...</option>
          <optgroup label="Activities">
            {options
              .filter((o) => o.type === "activity")
              .map((o) => (
                <option key={encodeOption(o.type, o.id)} value={encodeOption(o.type, o.id)}>
                  {o.label}
                </option>
              ))}
          </optgroup>
          <optgroup label="Milestones">
            {options
              .filter((o) => o.type === "milestone")
              .map((o) => (
                <option key={encodeOption(o.type, o.id)} value={encodeOption(o.type, o.id)}>
                  {o.label}
                </option>
              ))}
          </optgroup>
        </select>
        <label className="dependency-form__lag">
          Lag (days)
          <input
            type="number"
            value={lagDays}
            onChange={(e) => setLagDays(Number(e.target.value))}
          />
        </label>
        <button type="submit" className="button button--primary" disabled={createMutation.isPending}>
          Add dependency
        </button>
      </form>
      )}
      {formError && <p className="form-error">{formError}</p>}

      {dependencies && dependencies.length === 0 && <p>No dependencies yet.</p>}

      {dependencies && dependencies.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Predecessor</th>
              <th>Type</th>
              <th>Successor</th>
              <th>Lag (days)</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {dependencies.map((dep) => (
              <tr key={dep.id}>
                <td>
                  {dep.predecessor_label}{" "}
                  {dep.predecessor_type === "milestone" && <span className="tag-chip">milestone</span>}
                </td>
                <td>Finish → Start</td>
                <td>
                  {dep.successor_label}{" "}
                  {dep.successor_type === "milestone" && <span className="tag-chip">milestone</span>}
                </td>
                <td>{dep.lag_days}</td>
                <td>
                  {canManageDependencies && (
                    <button
                      type="button"
                      className="button button--danger"
                      onClick={() => {
                        if (confirm(`Remove dependency "${dep.predecessor_label}" → "${dep.successor_label}"?`)) {
                          deleteMutation.mutate(dep.id);
                        }
                      }}
                    >
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
