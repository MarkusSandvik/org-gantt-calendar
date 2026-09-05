import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { InvitationPreview, Me } from "../api/types";
import { ME_QUERY_KEY } from "../hooks/useAuth";

const ROLE_LABELS: Record<string, string> = { member: "Member", lead: "Lead" };

export function AcceptInvitation() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const token = searchParams.get("token") ?? "";

  const { data: preview, isLoading, error } = useQuery({
    queryKey: ["invitation-preview", token],
    queryFn: () => api.get<InvitationPreview>(`/invitations/preview/${token}`),
    enabled: token.length > 0,
    retry: false,
  });

  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    setSubmitting(true);
    try {
      const me = await api.post<Me>("/invitations/accept", { token, password });
      queryClient.setQueryData(ME_QUERY_KEY, me);
      navigate("/", { replace: true });
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Could not accept invitation");
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1>Accept invitation</h1>
          <p className="form-error">This link is missing its invitation token.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Accept invitation</h1>
        {isLoading && <p>Loading invitation...</p>}
        {error && <p className="form-error">This invitation link is invalid or has expired.</p>}
        {preview && (
          <>
            <p>
              You're invited as <strong>{preview.name}</strong> ({preview.email})
              {preview.team_name && (
                <>
                  {" "}
                  to join <strong>{preview.team_name}</strong>
                </>
              )}
              {preview.target_team_role && (
                <> as a {ROLE_LABELS[preview.target_team_role]}</>
              )}
              {preview.target_global_role === "admin" && <> as an Admin</>}.
            </p>
            <form onSubmit={handleSubmit}>
              <label>
                Set a password
                <input
                  type="password"
                  required
                  minLength={8}
                  autoFocus
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              {errorMessage && <p className="form-error">{errorMessage}</p>}
              <button
                type="submit"
                className="button button--primary auth-card__submit"
                disabled={submitting}
              >
                Create account
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
