import { Navigate, Outlet, Route, Routes, useLocation, useParams } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { RequireAuth } from "./components/layout/RequireAuth";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { AcceptInvitation } from "./pages/AcceptInvitation";
import { ActivitiesAdmin } from "./pages/admin/ActivitiesAdmin";
import { BaselinesAdmin } from "./pages/admin/BaselinesAdmin";
import { DependenciesAdmin } from "./pages/admin/DependenciesAdmin";
import { ImportExportAdmin } from "./pages/admin/ImportExportAdmin";
import { ProjectsAdmin } from "./pages/admin/ProjectsAdmin";
import { TagsAdmin } from "./pages/admin/TagsAdmin";
import { TeamsAdmin } from "./pages/admin/TeamsAdmin";
import { UsersAdmin } from "./pages/admin/UsersAdmin";
import { CalendarMonthPage } from "./pages/calendar/CalendarMonthPage";
import { CalendarWeekPage } from "./pages/calendar/CalendarWeekPage";
import { CalendarYearPage } from "./pages/calendar/CalendarYearPage";
import { ProjectProvider, useProject } from "./contexts/ProjectContext";
import { Dashboard } from "./pages/Dashboard";
import { Gantt } from "./pages/Gantt";
import { Login } from "./pages/Login";
import { MilestonesPage } from "./pages/milestones/MilestonesPage";
import { MyTasks } from "./pages/MyTasks";
import { NotFound } from "./pages/NotFound";
import { ResetPassword } from "./pages/ResetPassword";

// Every project-scoped page used to live at a flat path like "/gantt" or
// "/admin/activities". These are kept working as redirects into the
// equivalent "/:projectSlug/..." URL (Section 8) so old bookmarks and links
// never 404 — they just land on the project the user was last using.
const LEGACY_PROJECT_PATHS = [
  "gantt",
  "calendar",
  "calendar/month/:year/:month",
  "calendar/week/:isoYear/:isoWeek",
  "calendar/year",
  "calendar/year/:year",
  "milestones",
  "my-tasks",
  "admin",
  "admin/activities",
  "admin/teams",
  "admin/tags",
  "admin/dependencies",
  "admin/baselines",
  "admin/import-export",
  "admin/users",
];

function LegacyRedirect() {
  const { project, isLoading } = useProject();
  const location = useLocation();
  if (isLoading || !project) return null;
  return <Navigate to={`/${project.slug}${location.pathname}${location.search}`} replace />;
}

function RootRedirect() {
  const { project, isLoading } = useProject();
  if (isLoading || !project) return null;
  return <Navigate to={`/${project.slug}`} replace />;
}

/** Guards the ":projectSlug" segment: a slug that doesn't match any real
 * project 404s rather than silently falling back to some other project's
 * data, matching this app's project-isolation principle. */
function ProjectSlugGuard() {
  const { projectSlug } = useParams();
  const { projects, isLoading } = useProject();
  if (isLoading) return null;
  if (!projects.some((p) => p.slug === projectSlug)) return <NotFound />;
  return <AppShell />;
}

export function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route path="accept-invitation" element={<AcceptInvitation />} />
      <Route path="reset-password" element={<ResetPassword />} />

      <Route element={<RequireAuth />}>
        <Route
          element={
            <ProjectProvider>
              <Outlet />
            </ProjectProvider>
          }
        >
          <Route index element={<RootRedirect />} />
          {LEGACY_PROJECT_PATHS.map((path) => (
            <Route key={path} path={path} element={<LegacyRedirect />} />
          ))}

          <Route path=":projectSlug" element={<ProjectSlugGuard />}>
            <Route index element={<Dashboard />} />
            <Route path="gantt" element={<Gantt />} />
            <Route path="calendar" element={<CalendarMonthPage />} />
            <Route path="calendar/month/:year/:month" element={<CalendarMonthPage />} />
            <Route path="calendar/week/:isoYear/:isoWeek" element={<CalendarWeekPage />} />
            <Route path="calendar/year" element={<CalendarYearPage />} />
            <Route path="calendar/year/:year" element={<CalendarYearPage />} />
            <Route path="milestones" element={<MilestonesPage />} />
            <Route path="my-tasks" element={<MyTasks />} />
            <Route path="admin" element={<AdminLayout />}>
              <Route index element={<Navigate to="activities" replace />} />
              <Route path="activities" element={<ActivitiesAdmin />} />
              <Route path="teams" element={<TeamsAdmin />} />
              <Route path="tags" element={<TagsAdmin />} />
              <Route path="dependencies" element={<DependenciesAdmin />} />
              <Route path="baselines" element={<BaselinesAdmin />} />
              <Route path="import-export" element={<ImportExportAdmin />} />
              <Route path="users" element={<UsersAdmin />} />
              <Route path="projects" element={<ProjectsAdmin />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
