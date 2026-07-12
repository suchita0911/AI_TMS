import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Users,
  Building2,
  UsersRound,
  BookOpen,
  CheckCircle2,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import { EnrollmentStatusBadge, CourseTypeBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageLoader } from "@/components/ui/spinner";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import type { Page, User, Department, Group, MyCourse } from "@/types";

function AdminDashboard() {
  const employees = useQuery({
    queryKey: ["users", { role: "employee", count: true }],
    queryFn: async () =>
      (await api.get<Page<User>>("/users", { params: { role: "employee", page_size: 1 } })).data,
  });
  const departments = useQuery({
    queryKey: ["departments", { count: true }],
    queryFn: async () =>
      (await api.get<Page<Department>>("/departments", { params: { page_size: 1 } })).data,
  });
  const groups = useQuery({
    queryKey: ["groups", { count: true }],
    queryFn: async () =>
      (await api.get<Page<Group>>("/groups", { params: { page_size: 1 } })).data,
  });
  const courses = useQuery({
    queryKey: ["courses", { count: true }],
    queryFn: async () =>
      (await api.get<Page<{ id: number }>>("/courses", { params: { page_size: 1 } })).data,
  });

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Courses" value={courses.data?.total ?? "—"} icon={BookOpen} to="/admin/courses" />
      <StatCard label="Employees" value={employees.data?.total ?? "—"} icon={Users} tone="success" to="/admin/employees" />
      <StatCard label="Departments" value={departments.data?.total ?? "—"} icon={Building2} tone="warning" to="/admin/departments" />
      <StatCard label="Groups" value={groups.data?.total ?? "—"} icon={UsersRound} tone="primary" to="/admin/groups" />
    </div>
  );
}

function EmployeeDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-courses"],
    queryFn: async () => (await api.get<MyCourse[]>("/me/courses")).data,
  });

  if (isLoading) return <PageLoader />;
  const courses = data ?? [];
  const mandatory = courses.filter((c) => c.course_type === "mandatory").length;
  const completed = courses.filter((c) => c.status === "completed").length;
  const pending = courses.filter((c) => c.status !== "completed").length;
  const overdue = courses.filter((c) => c.is_overdue).length;

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Assigned" value={courses.length} icon={BookOpen} to="/my-courses" />
        <StatCard label="Mandatory" value={mandatory} icon={AlertTriangle} tone="warning" to="/my-courses" />
        <StatCard label="Completed" value={completed} icon={CheckCircle2} tone="success" to="/my-courses" />
        <StatCard label="Pending" value={pending} icon={Clock} tone="primary" to="/my-courses" />
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Your courses</CardTitle>
          <Button variant="outline" size="sm" asChild>
            <Link to="/my-courses">View all</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {courses.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              You have no assigned courses yet.
            </p>
          ) : (
            <ul className="divide-y">
              {courses.slice(0, 5).map((c) => (
                <li key={c.course_id} className="flex items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <Link to={`/my-courses/${c.course_id}`} className="text-sm font-medium hover:underline">
                      {c.name}
                    </Link>
                  </div>
                  <CourseTypeBadge type={c.course_type} />
                  <EnrollmentStatusBadge status={c.status} />
                </li>
              ))}
            </ul>
          )}
          {overdue > 0 && (
            <p className="mt-3 text-xs text-destructive">
              ⚠ {overdue} course{overdue > 1 ? "s are" : " is"} overdue.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  if (!user) return <PageLoader />;

  return (
    <div>
      <PageHeader
        title={`Welcome, ${user.first_name}`}
        description={
          user.role === "admin"
            ? "Overview of your organisation's training program"
            : "Your training overview"
        }
      />
      {user.role === "admin" ? <AdminDashboard /> : <EmployeeDashboard />}
    </div>
  );
}
