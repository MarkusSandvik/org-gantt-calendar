import { NavLink, Outlet } from "react-router-dom";
import { usePermissions } from "../../hooks/usePermissions";

const SECTIONS: {
  label: string;
  to: string | null;
  note: string;
  requiresUserAdmin?: boolean;
  requiresAdmin?: boolean;
}[] = [
  { label: "Activities", to: "activities", note: "" },
  { label: "Teams", to: "teams", note: "" },
  { label: "Tags", to: "tags", note: "" },
  { label: "Users", to: "users", note: "", requiresUserAdmin: true },
  { label: "Dependencies", to: "dependencies", note: "" },
  { label: "Baselines", to: "baselines", note: "" },
  { label: "Import / Export", to: "import-export", note: "" },
  { label: "Projects", to: "projects", note: "", requiresAdmin: true },
  { label: "Settings", to: null, note: "Arrives in a later phase" },
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
        {sections.map((section) =>
          section.to ? (
            <NavLink
              key={section.label}
              to={section.to}
              className={({ isActive }) =>
                isActive ? "admin-tab admin-tab--active" : "admin-tab"
              }
            >
              {section.label}
            </NavLink>
          ) : (
            <span key={section.label} className="admin-tab admin-tab--disabled" title={section.note}>
              {section.label}
            </span>
          ),
        )}
      </nav>
      <div className="admin-tab-content">
        <Outlet />
      </div>
    </div>
  );
}
