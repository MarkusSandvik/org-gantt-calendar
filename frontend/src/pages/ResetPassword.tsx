import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    try {
      await api.post("/auth/password-reset/confirm", { token, new_password: password });
      setDone(true);
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Reset failed");
    }
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1>Reset password</h1>
          <p className="form-error">This link is missing its reset token.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Reset password</h1>
        {done ? (
          <>
            <p>Your password has been reset. You can now log in.</p>
            <button className="button button--primary auth-card__submit" onClick={() => navigate("/login")}>
              Go to login
            </button>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <label>
              New password
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
            <button type="submit" className="button button--primary auth-card__submit">
              Set new password
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
