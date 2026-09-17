import { NavLink, Outlet } from "react-router-dom";
import { usePermissions } from "../../hooks/usePermissions";

const SECTIONS: {
  label: string;
  to: string;
  requiresUserAdmin?: boolean;
  requiresAdmin?: boolean;
}[] = [
  { label: "Activities", to: "activities" },
  { label: "Teams", to: "teams" },
  { label: "Tags", to: "tags" },
  { label: "Users", to: "users", requiresUserAdmin: true },
  { label: "Dependencies", to: "dependencies" },
  { label: "Baselines", to: "baselines" },
  { label: "Import / Export", to: "import-export" },
  { label: "Projects", to: "projects", requiresAdmin: true },
  { label: "Settings", to: "settings", requiresAdmin: true },
];

export function AdminLayout() {
  const { canViewUserAdmin, isAdmin } = usePermissions();
  const sections = SECTIONS.filter(
    (s) => (!s.requiresUserAdmin || canViewUserAdmin) && (!s.requiresAdmin || isAdmin),
  );

  return (
    <div className="page">
      <h1>Admin</h1>
      <nav className="admin-tabs">
        {sections.map((section) => (
          <NavLink
            key={section.label}
            to={section.to}
            className={({ isActive }) =>
              isActive ? "admin-tab admin-tab--active" : "admin-tab"
            }
          >
            {section.label}
          </NavLink>
        ))}
      </nav>
      <div className="admin-tab-content">
        <Outlet />
      </div>
    </div>
  );
}
