import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, FileText, HelpCircle, CalendarClock } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { CourseTypeBadge, EnrollmentStatusBadge } from "@/components/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { MyCourse } from "@/types";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "mandatory", label: "Mandatory" },
  { key: "optional", label: "Optional" },
  { key: "pending", label: "Pending" },
  { key: "completed", label: "Completed" },
] as const;

export default function MyCoursesPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["key"]>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["my-courses"],
    queryFn: async () => (await api.get<MyCourse[]>("/me/courses")).data,
  });

  if (isLoading) return <PageLoader />;

  const courses = (data ?? []).filter((c) => {
    if (filter === "all") return true;
    if (filter === "mandatory") return c.course_type === "mandatory";
    if (filter === "optional") return c.course_type === "optional";
    if (filter === "completed") return c.status === "completed";
    if (filter === "pending") return c.status !== "completed";
    return true;
  });

  return (
    <div>
      <PageHeader title="My Courses" description="Courses assigned to you" />

      <div className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <Button
            key={f.key}
            size="sm"
            variant={filter === f.key ? "default" : "outline"}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </Button>
        ))}
      </div>

      {courses.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <BookOpen className="h-10 w-10 opacity-40" />
            <p>No courses in this view.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {courses.map((c) => (
            <Link key={c.course_id} to={`/my-courses/${c.course_id}`}>
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
                  <CourseTypeBadge type={c.course_type} />
                  <div className="flex items-center gap-4 border-t pt-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <FileText className="h-3.5 w-3.5" /> {c.document_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <HelpCircle className="h-3.5 w-3.5" /> {c.quiz_question_count} Qs
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
