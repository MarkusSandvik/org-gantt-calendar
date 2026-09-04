import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api, ApiError } from "../../api/client";
import type {
  ImportApplyResponse,
  ImportPreviewResponse,
  ImportRowResult,
  Project,
} from "../../api/types";

function RowErrors({ row }: { row: ImportRowResult }) {
  if (row.errors.length === 0) {
    return <span className="import-row-status import-row-status--ok">Ready</span>;
  }
  return (
    <ul className="import-row-errors">
      {row.errors.map((err, i) => (
        <li key={i}>{err}</li>
      ))}
    </ul>
  );
}

function ImportResultTable({ rows }: { rows: ImportRowResult[] }) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Title</th>
          <th>Start</th>
          <th>End</th>
          <th>Owner team</th>
          <th>Owner user</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.row_number}
            className={row.errors.length > 0 ? "data-table__row--error" : ""}
          >
            <td>{row.row_number}</td>
            <td>{row.title || <em>(blank)</em>}</td>
            <td>{row.start_date}</td>
            <td>{row.end_date}</td>
            <td>{row.owner_team}</td>
            <td>{row.owner_user}</td>
            <td>
              <RowErrors row={row} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ImportExportAdmin() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [applyResult, setApplyResult] = useState<ImportApplyResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<Project[]>("/projects"),
  });
  const projectId = projects?.[0]?.id;

  const previewMutation = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.postForm<ImportPreviewResponse>(
        `/import/activities/preview?project_id=${projectId}`,
        formData,
      );
    },
    onSuccess: (result) => {
      setPreview(result);
      setApplyResult(null);
      setErrorMessage(null);
    },
    onError: (err: ApiError) => {
      setErrorMessage(err.message);
      setPreview(null);
    },
  });

  const applyMutation = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.postForm<ImportApplyResponse>(
        `/import/activities/apply?project_id=${projectId}`,
        formData,
      );
    },
    onSuccess: (result) => {
      setApplyResult(result);
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
    onError: (err: ApiError) => setErrorMessage(err.message),
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    setPreview(null);
    setApplyResult(null);
    setErrorMessage(null);
    if (file && projectId != null) {
      previewMutation.mutate(file);
    }
  }

  function reset() {
    setSelectedFile(null);
    setPreview(null);
    setApplyResult(null);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  if (!projectId) {
    return <p>Loading project...</p>;
  }

  return (
    <div>
      <h2>Export</h2>
      <p className="page__phase-note">
        Download the current plan. The activities CSV uses the same column
        layout as import, so it can be edited and re-imported unchanged.
      </p>
      <div className="toolbar">
        <a
          className="button"
          href={`/api/v1/export/activities.csv?project_id=${projectId}`}
          download="activities_export.csv"
        >
          Export activities (CSV)
        </a>
        <a
          className="button"
          href={`/api/v1/export/plan.xlsx?project_id=${projectId}`}
          download="plan_export.xlsx"
        >
          Export full plan (XLSX)
        </a>
      </div>

      <h2>Import</h2>
      <p className="page__phase-note">
        Bulk-create activities from a CSV or XLSX file. Nothing is written to
        the plan until you review the preview below and confirm the import.
      </p>

      <div className="toolbar">
        <a
          className="button"
          href="/api/v1/import/activities/template"
          download="activity_import_template.csv"
        >
          Download CSV template
        </a>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx"
          onChange={handleFileChange}
        />
        {selectedFile && (
          <button className="button" onClick={reset}>
            Clear
          </button>
        )}
      </div>

      {errorMessage && <p className="form-error">{errorMessage}</p>}
      {previewMutation.isPending && <p>Reading file...</p>}

      {preview && !applyResult && (
        <div>
          <h2>Preview</h2>
          <p>
            {preview.valid_count} row{preview.valid_count === 1 ? "" : "s"} ready to
            import
            {preview.error_count > 0 &&
              `, ${preview.error_count} row${preview.error_count === 1 ? "" : "s"} with errors (these will be skipped)`}
            .
          </p>
          <ImportResultTable rows={preview.rows} />
          <div className="modal-actions">
            <div className="modal-actions__spacer" />
            <button
              className="button button--primary"
              disabled={preview.valid_count === 0 || applyMutation.isPending}
              onClick={() => selectedFile && applyMutation.mutate(selectedFile)}
            >
              Import {preview.valid_count} row{preview.valid_count === 1 ? "" : "s"}
            </button>
          </div>
        </div>
      )}

      {applyResult && (
        <div>
          <h2>Import complete</h2>
          <p>
            Created {applyResult.created_count} activit
            {applyResult.created_count === 1 ? "y" : "ies"}
            {applyResult.skipped_count > 0 &&
              `, skipped ${applyResult.skipped_count} row${applyResult.skipped_count === 1 ? "" : "s"} with errors`}
            .
          </p>
          <ImportResultTable rows={applyResult.rows} />
        </div>
      )}
    </div>
  );
}
