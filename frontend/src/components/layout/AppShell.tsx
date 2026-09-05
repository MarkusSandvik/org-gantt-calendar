import { NavLink, Outlet } from "react-router-dom";
import { useCurrentUser, useLogout } from "../../hooks/useAuth";
import { GlobalSearch } from "./GlobalSearch";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/gantt", label: "Gantt" },
  { to: "/calendar", label: "Calendar" },
  { to: "/milestones", label: "Milestones" },
  { to: "/my-tasks", label: "My Tasks" },
  { to: "/admin", label: "Admin" },
];

function CurrentUserBadge() {
  const { me } = useCurrentUser();
  const logout = useLogout();

  if (!me) return null;

  const roleLabel =
    me.global_role === "admin"
      ? "Admin"
      : me.team_memberships.some((m) => m.team_role === "lead")
        ? "Lead"
        : "Member";

  return (
    <div className="current-user-badge">
      <span>
        {me.name} <span className="current-user-badge__role">({roleLabel})</span>
      </span>
      <button className="button" onClick={() => logout.mutate()}>
        Log out
      </button>
    </div>
  );
}

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
          <CurrentUserBadge />
        </div>
        <Outlet />
      </main>
    </div>
  );
}
