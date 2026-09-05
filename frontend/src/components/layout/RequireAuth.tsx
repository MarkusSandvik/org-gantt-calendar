import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useCurrentUser } from "../../hooks/useAuth";

export function RequireAuth() {
  const { me, isLoading, isUnauthenticated } = useCurrentUser();
  const location = useLocation();

  if (isLoading) {
    return <p style={{ padding: 24 }}>Loading...</p>;
  }
  if (isUnauthenticated || !me) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
