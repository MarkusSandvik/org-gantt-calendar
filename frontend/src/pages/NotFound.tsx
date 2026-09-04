import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="page">
      <h1>Page not found</h1>
      <p className="page__phase-note">
        That page doesn't exist. <Link to="/">Back to the Dashboard</Link>.
      </p>
    </div>
  );
}
