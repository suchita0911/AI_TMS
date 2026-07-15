import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/components/layout/AppLayout";
import { PageLoader } from "@/components/ui/spinner";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import SetPasswordPage from "@/pages/auth/SetPasswordPage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import SsoCallbackPage from "@/pages/auth/SsoCallbackPage";
import DashboardPage from "@/pages/DashboardPage";
import EmployeesPage from "@/pages/admin/EmployeesPage";
import EmployeeDetailPage from "@/pages/admin/EmployeeDetailPage";
import DepartmentsPage from "@/pages/admin/DepartmentsPage";
import GroupsPage from "@/pages/admin/GroupsPage";
import CoursesPage from "@/pages/admin/CoursesPage";
import TrendingCoursesPage from "@/pages/admin/TrendingCoursesPage";
import CourseDetailPage from "@/pages/admin/CourseDetailPage";
import QuestionBankPage from "@/pages/admin/QuestionBankPage";
import ReportsPage from "@/pages/admin/ReportsPage";
import MyCoursesPage from "@/pages/employee/MyCoursesPage";
import CourseViewerPage from "@/pages/employee/CourseViewerPage";
import QuizPage from "@/pages/employee/QuizPage";
import CertificatePage from "@/pages/employee/CertificatePage";
import VerifyPage from "@/pages/VerifyPage";

function PublicOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (user) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Public auth routes */}
      <Route path="/login" element={<PublicOnly><LoginPage /></PublicOnly>} />
      <Route path="/register" element={<PublicOnly><RegisterPage /></PublicOnly>} />
      <Route path="/set-password" element={<SetPasswordPage mode="setup" />} />
      <Route path="/reset-password" element={<SetPasswordPage mode="reset" />} />
      <Route path="/forgot-password" element={<PublicOnly><ForgotPasswordPage /></PublicOnly>} />
      {/* SSO redirect target — consumes tokens from the URL fragment */}
      <Route path="/sso/callback" element={<SsoCallbackPage />} />
      {/* Public certificate verification (QR target) */}
      <Route path="/verify/:number" element={<VerifyPage />} />

      {/* Authenticated app */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/my-courses" element={<MyCoursesPage />} />
          <Route path="/my-courses/:id" element={<CourseViewerPage />} />
          <Route path="/my-courses/:id/quiz" element={<QuizPage />} />
          <Route path="/my-courses/:id/certificate" element={<CertificatePage />} />
        </Route>
      </Route>

      {/* Admin-only */}
      <Route element={<ProtectedRoute roles={["admin"]} />}>
        <Route element={<AppLayout />}>
          <Route path="/admin/courses" element={<CoursesPage />} />
          <Route path="/admin/trending" element={<TrendingCoursesPage />} />
          <Route path="/admin/courses/:id" element={<CourseDetailPage />} />
          <Route path="/admin/courses/:id/questions" element={<QuestionBankPage />} />
          <Route path="/admin/employees" element={<EmployeesPage />} />
          <Route path="/admin/employees/:id" element={<EmployeeDetailPage />} />
          <Route path="/admin/departments" element={<DepartmentsPage />} />
          <Route path="/admin/groups" element={<GroupsPage />} />
          <Route path="/admin/reports" element={<ReportsPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
