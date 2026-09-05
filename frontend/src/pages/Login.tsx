import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { branding } from "../branding";
import { useLogin } from "../hooks/useAuth";

export function Login() {
  const navigate = useNavigate();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [showReset, setShowReset] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetSent, setResetSent] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    login.mutate(
      { email, password },
      {
        onSuccess: () => navigate("/", { replace: true }),
        onError: (err) => setErrorMessage(err instanceof ApiError ? err.message : "Login failed"),
      },
    );
  }

  async function handleResetRequest(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/auth/password-reset/request", { email: resetEmail });
    setResetSent(true);
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>{branding.productName}</h1>

        {!showReset && (
          <form onSubmit={handleSubmit}>
            <label>
              Email
              <input
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>

            {errorMessage && <p className="form-error">{errorMessage}</p>}

            <button
              type="submit"
              className="button button--primary auth-card__submit"
              disabled={login.isPending}
            >
              Log in
            </button>
            <button
              type="button"
              className="auth-card__link"
              onClick={() => setShowReset(true)}
            >
              Forgot your password?
            </button>
          </form>
        )}

        {showReset && (
          <form onSubmit={handleResetRequest}>
            {resetSent ? (
              <p>
                If that email has an account, a reset link has been generated. In local
                development, check the backend server's console output for the link.
              </p>
            ) : (
              <>
                <label>
                  Email
                  <input
                    type="email"
                    required
                    autoFocus
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                  />
                </label>
                <button type="submit" className="button button--primary auth-card__submit">
                  Send reset link
                </button>
              </>
            )}
            <button
              type="button"
              className="auth-card__link"
              onClick={() => {
                setShowReset(false);
                setResetSent(false);
              }}
            >
              Back to login
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
