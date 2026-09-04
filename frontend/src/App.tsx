import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { ActivitiesAdmin } from "./pages/admin/ActivitiesAdmin";
import { BaselinesAdmin } from "./pages/admin/BaselinesAdmin";
import { DependenciesAdmin } from "./pages/admin/DependenciesAdmin";
import { CalendarMonthPage } from "./pages/calendar/CalendarMonthPage";
import { CalendarWeekPage } from "./pages/calendar/CalendarWeekPage";
import { Dashboard } from "./pages/Dashboard";
import { Gantt } from "./pages/Gantt";
import { MilestonesPage } from "./pages/milestones/MilestonesPage";
import { MyTasks } from "./pages/MyTasks";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="gantt" element={<Gantt />} />
        <Route path="calendar" element={<CalendarMonthPage />} />
        <Route path="calendar/week/:isoYear/:isoWeek" element={<CalendarWeekPage />} />
        <Route path="milestones" element={<MilestonesPage />} />
        <Route path="my-tasks" element={<MyTasks />} />
        <Route path="admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="activities" replace />} />
          <Route path="activities" element={<ActivitiesAdmin />} />
          <Route path="dependencies" element={<DependenciesAdmin />} />
          <Route path="baselines" element={<BaselinesAdmin />} />
        </Route>
      </Route>
    </Routes>
  );
}
