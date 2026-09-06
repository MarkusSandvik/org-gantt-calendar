import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { branding } from "../../branding";
import { useCurrentUser, useLogout } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import type { ThemePreference } from "../../hooks/useTheme";
import { GlobalSearch } from "./GlobalSearch";

const THEME_CYCLE: ThemePreference[] = ["system", "light", "dark"];
const THEME_LABEL: Record<ThemePreference, string> = {
  system: "Theme: System",
  light: "Theme: Light",
  dark: "Theme: Dark",
};

function ThemeToggle() {
  const { preference, setPreference } = useTheme();

  function cycle() {
    const next = THEME_CYCLE[(THEME_CYCLE.indexOf(preference) + 1) % THEME_CYCLE.length];
    setPreference(next);
  }

  return (
    <button className="app-nav__theme-toggle" onClick={cycle} title="Cycle theme">
      {THEME_LABEL[preference]}
    </button>
  );
}

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
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      {navOpen && <div className="app-nav-backdrop" onClick={() => setNavOpen(false)} />}
      <aside className={navOpen ? "app-nav app-nav--open" : "app-nav"}>
        <div className="app-nav__brand">
          {branding.logoHref ? (
            <img className="app-nav__logo" src={branding.logoHref} alt={branding.productName} />
          ) : (
            branding.productName
          )}
        </div>
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
        <div className="app-nav__footer">
          <ThemeToggle />
          <p className="app-nav__credit">
            Created by Markus Sandvik
            <br />© {new Date().getFullYear()}
          </p>
        </div>
      </aside>
      <main className="app-content">
        <div className="app-content__topbar">
          <button
            type="button"
            className="app-nav__menu-toggle"
            onClick={() => setNavOpen((open) => !open)}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>
          <GlobalSearch />
          <CurrentUserBadge />
        </div>
        <Outlet />
      </main>
    </div>
  );
}
