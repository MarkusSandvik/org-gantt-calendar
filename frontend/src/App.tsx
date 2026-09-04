import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { AdminLayout } from "./pages/admin/AdminLayout";
import { ActivitiesAdmin } from "./pages/admin/ActivitiesAdmin";
import { DependenciesAdmin } from "./pages/admin/DependenciesAdmin";
import { Calendar } from "./pages/Calendar";
import { Dashboard } from "./pages/Dashboard";
import { Gantt } from "./pages/Gantt";
import { Milestones } from "./pages/Milestones";
import { MyTasks } from "./pages/MyTasks";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="gantt" element={<Gantt />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="milestones" element={<Milestones />} />
        <Route path="my-tasks" element={<MyTasks />} />
        <Route path="admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="activities" replace />} />
          <Route path="activities" element={<ActivitiesAdmin />} />
          <Route path="dependencies" element={<DependenciesAdmin />} />
        </Route>
      </Route>
    </Routes>
  );
}
