import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Mail,
  Building2,
  HelpCircle,
  CalendarClock,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import {
  CourseTypeBadge,
  EnrollmentStatusBadge,
  UserStatusBadge,
} from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { MyCourse, User } from "@/types";

export default function EmployeeDetailPage() {
  const { id } = useParams();
  const userId = Number(id);

  const user = useQuery({
    queryKey: ["user", userId],
    queryFn: async () => (await api.get<User>(`/users/${userId}`)).data,
  });
  const courses = useQuery({
    queryKey: ["user-courses", userId],
    queryFn: async () => (await api.get<MyCourse[]>(`/users/${userId}/courses`)).data,
  });

  if (user.isLoading || !user.data) return <PageLoader />;
  const u = user.data;
  const list = courses.data ?? [];
  const completed = list.filter((c) => c.status === "completed").length;
  const pending = list.filter((c) => c.status !== "completed").length;
  const overdue = list.filter((c) => c.is_overdue).length;

  return (
    <div>
      <Link
        to="/admin/employees"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to employees
      </Link>

      <PageHeader
        title={`${u.first_name} ${u.last_name}`}
        description="Assigned courses and progress"
        actions={<UserStatusBadge status={u.status} />}
      />

      <div className="mb-5 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <Mail className="h-4 w-4" /> {u.email}
        </span>
        <span className="flex items-center gap-1.5">
          <Building2 className="h-4 w-4" /> {u.department?.name ?? "No department"}
        </span>
        <Badge variant={u.role === "admin" ? "default" : "secondary"}>{u.role}</Badge>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Assigned" value={list.length} icon={BookOpen} />
        <StatCard label="Completed" value={completed} icon={CheckCircle2} tone="success" />
        <StatCard label="Pending" value={pending} icon={Clock} tone="primary" />
        <StatCard label="Overdue" value={overdue} icon={AlertTriangle} tone="destructive" />
      </div>

      {courses.isLoading ? (
        <PageLoader />
      ) : list.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <BookOpen className="h-10 w-10 opacity-40" />
            <p>No courses assigned to this employee yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {list.map((c) => (
            <Link key={c.course_id} to={`/admin/courses/${c.course_id}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="flex h-full flex-col gap-3 p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <BookOpen className="h-5 w-5" />
                    </div>
                    <EnrollmentStatusBadge status={c.status} />
                  </div>
                  <div className="flex-1">
                    <h3 className="line-clamp-1 font-semibold">{c.name}</h3>
                    <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                      {c.description || "No description"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <CourseTypeBadge type={c.course_type} />
                    {c.best_score != null && (
                      <span className="text-xs text-muted-foreground">
                        Best score {c.best_score}%
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 border-t pt-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <HelpCircle className="h-3.5 w-3.5" /> {c.quiz_question_count} Qs
                    </span>
                    <span>
                      Attempts {c.attempts_used}/{c.max_attempts}
                    </span>
                    {c.end_date && (
                      <span className="flex items-center gap-1">
                        <CalendarClock className="h-3.5 w-3.5" /> {formatDate(c.end_date)}
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
