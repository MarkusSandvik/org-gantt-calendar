import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { Tag, TagCreatePayload, TagUpdatePayload } from "../../api/types";
import { useToast } from "../../components/Toast";
import { useProject } from "../../contexts/ProjectContext";
import { usePermissions } from "../../hooks/usePermissions";
import { TagFormModal } from "./TagFormModal";

export function TagsAdmin() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { canManageTags } = usePermissions();

  const { project, canEdit } = useProject();
  const projectId = project?.id;

  const { data: tags, isLoading } = useQuery({
    queryKey: ["tags", { projectId }],
    queryFn: () => api.get<Tag[]>(`/tags?project_id=${projectId}`),
    enabled: projectId != null,
  });

  const [modalTag, setModalTag] = useState<Tag | null | undefined>(undefined);
  const [formError, setFormError] = useState<string | null>(null);

  function closeModal() {
    setModalTag(undefined);
    setFormError(null);
  }

  const createMutation = useMutation({
    mutationFn: (payload: TagCreatePayload) => api.post<Tag>("/tags", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      closeModal();
      showToast("Tag created");
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: TagUpdatePayload }) =>
      api.patch<Tag>(`/tags/${id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      closeModal();
      showToast("Tag updated");
    },
    onError: (err: ApiError) => setFormError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/tags/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      closeModal();
      showToast("Tag deleted");
    },
    onError: (err: ApiError) => showToast(err.message, "error"),
  });

  if (!projectId || isLoading) {
    return <p>Loading tags...</p>;
  }

  return (
    <div>
      <div className="toolbar">
        <p className="page__phase-note">Every active tag available to apply to activities.</p>
        {canManageTags && canEdit && (
          <button className="button button--primary" onClick={() => setModalTag(null)}>
            New Tag
          </button>
        )}
      </div>

      {tags && tags.length === 0 && <p>No tags yet.</p>}

      {tags && tags.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Color</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tags.map((tag) => (
              <tr key={tag.id}>
                <td>
                  <span className="tag-swatch" style={{ background: tag.color ?? "#8a93a1" }} />
                  {tag.name}
                </td>
                <td>{tag.color ?? "—"}</td>
                <td>
                  {canManageTags && canEdit && (
                    <button className="button" onClick={() => setModalTag(tag)}>
                      Edit
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {modalTag !== undefined && (
        <TagFormModal
          projectId={projectId}
          tag={modalTag}
          submitting={createMutation.isPending || updateMutation.isPending}
          errorMessage={formError}
          onClose={closeModal}
          onSubmit={(payload) => {
            setFormError(null);
            if (modalTag) {
              updateMutation.mutate({ id: modalTag.id, payload: payload as TagUpdatePayload });
            } else {
              createMutation.mutate(payload as TagCreatePayload);
            }
          }}
          onDelete={
            modalTag && canEdit
              ? () => {
                  if (confirm(`Delete tag "${modalTag.name}"? This cannot be undone.`)) {
                    deleteMutation.mutate(modalTag.id);
                  }
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
