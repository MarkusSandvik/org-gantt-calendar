import { NavLink, Outlet } from "react-router-dom";

const SECTIONS: { label: string; to: string | null; note: string }[] = [
  { label: "Activities", to: "activities", note: "" },
  { label: "Teams", to: null, note: "Read-only for now — management UI lands with Tags/Users" },
  { label: "Tags", to: null, note: "Read-only for now — management UI lands with Teams/Users" },
  { label: "Users", to: null, note: "Read-only for now — management UI lands with Teams/Tags" },
  { label: "Dependencies", to: null, note: "Arrives in Phase 5" },
  { label: "Baselines", to: null, note: "Arrives in Phase 11" },
  { label: "Import / Export", to: null, note: "Arrives in Phase 12" },
  { label: "Settings", to: null, note: "Arrives in a later phase" },
];

export function AdminLayout() {
  return (
    <div className="page">
      <h1>Admin</h1>
      <nav className="admin-tabs">
        {SECTIONS.map((section) =>
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
