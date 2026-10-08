import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../state/AuthContext";

export default function ProtectedRoute({ roles }) {
  const { user, loading, organizations, organizationId } = useAuth();
  const location = useLocation();
  if (loading) return <div className="screen-center"><div className="loader" />Loading workspace</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!organizations.length && location.pathname !== "/organizations") return <Navigate to="/organizations" replace />;
  if (!organizationId) return <div className="screen-center">Choose an organization to continue.</div>;
  if (roles && !roles.includes("super_admin") && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
