import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import DashboardPage from "./pages/DashboardPage";
import MembersPage from "./pages/MembersPage";
import NotificationsPage from "./pages/NotificationsPage";
import OrganizationsPage from "./pages/OrganizationsPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import ProfilePage from "./pages/ProfilePage";
import SettingsPage from "./pages/SettingsPage";
import TaskDetailPage from "./pages/TaskDetailPage";
import TaskBoardPage from "./pages/TaskBoardPage";
import { useAuth } from "./state/AuthContext";

function OrganizationPage() {
  const { user } = useAuth();
  return user ? <OrganizationsPage /> : <Navigate to="/login" replace />;
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="tasks" element={<TaskBoardPage />} />
        <Route path="tasks/:taskId" element={<TaskDetailPage />} />
        <Route path="organizations" element={<OrganizationPage />} />
        <Route path="members" element={<MembersPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}
