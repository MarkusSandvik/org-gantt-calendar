import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { Admin } from "./pages/Admin";
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
        <Route path="admin" element={<Admin />} />
      </Route>
    </Routes>
  );
}
