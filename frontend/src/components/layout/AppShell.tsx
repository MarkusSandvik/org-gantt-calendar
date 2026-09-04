import { NavLink, Outlet } from "react-router-dom";
import { GlobalSearch } from "./GlobalSearch";
import { UserSwitcher } from "./UserSwitcher";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/gantt", label: "Gantt" },
  { to: "/calendar", label: "Calendar" },
  { to: "/milestones", label: "Milestones" },
  { to: "/my-tasks", label: "My Tasks" },
  { to: "/admin", label: "Admin" },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="app-nav">
        <div className="app-nav__brand">Org Planner</div>
        <nav>
          <ul>
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    isActive ? "app-nav__link app-nav__link--active" : "app-nav__link"
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <main className="app-content">
        <div className="app-content__topbar">
          <GlobalSearch />
          <UserSwitcher />
        </div>
        <Outlet />
      </main>
    </div>
  );
}
