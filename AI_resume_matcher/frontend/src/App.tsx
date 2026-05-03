import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import MatchPage from "./pages/MatchPage";
import ResultsPage from "./pages/ResultsPage";
import ResultDetailPage from "./pages/ResultDetailPage";
import AppShell from "./components/layout/AppShell";
import ProtectedRoute from "./components/common/ProtectedRoute";
import { isLoggedIn } from "./lib/auth";
import ResumesPage from "./pages/ResumesPage";
import JobsPage from "./pages/JobsPage";
import AgentPage from "./pages/AgentPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      <Route path="/login" element={<LoginRoute />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppShell>
              <DashboardPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/match"
        element={
          <ProtectedRoute>
            <AppShell>
              <MatchPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/results"
        element={
          <ProtectedRoute>
            <AppShell>
              <ResultsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/results/:id"
        element={
          <ProtectedRoute>
            <AppShell>
              <ResultDetailPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/agent"
        element={
          <ProtectedRoute>
            <AppShell>
              <AgentPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/resumes"
        element={
          <ProtectedRoute>
            <AppShell>
              <ResumesPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="/jobs"
        element={
          <ProtectedRoute>
            <AppShell>
              <JobsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route
        path="*"
        element={
          <div className="p-10">
            <h1 className="text-2xl font-semibold">404 页面不存在</h1>
            <p className="mt-2 text-slate-500">
              当前路径没有匹配到任何路由。
            </p>
          </div>
        }
      />
    </Routes>
  );
}

function LoginRoute() {
  const navigate = useNavigate();

  if (isLoggedIn()) {
    return <Navigate to="/dashboard" replace />;
  }

  return <LoginPage onLoginSuccess={() => navigate("/dashboard")} />;
}