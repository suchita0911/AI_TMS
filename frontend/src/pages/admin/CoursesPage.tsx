import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, BookOpen, FileText, HelpCircle, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { CourseStatusBadge, CourseTypeBadge } from "@/components/StatusBadge";
import { CourseFormDialog } from "@/components/CourseFormDialog";
import { AICourseDialog, type AICoursePayload } from "@/components/AICourseDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, apiError } from "@/lib/api";
import type { Course, CourseDetail, Page } from "@/types";

const PAGE_SIZE = 9;

export default function CoursesPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [aiDialogOpen, setAiDialogOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["courses", { search, statusFilter, page }],
    queryFn: async () =>
      (
        await api.get<Page<Course>>("/courses", {
          params: {
            q: search || undefined,
            status: statusFilter === "all" ? undefined : statusFilter,
            page,
            page_size: PAGE_SIZE,
          },
        })
      ).data,
  });

  const create = useMutation({
    mutationFn: async (payload: any) => (await api.post<CourseDetail>("/courses", payload)).data,
    onSuccess: () => {
      toast.success("Course created");
      setDialogOpen(false);
      qc.invalidateQueries({ queryKey: ["courses"] });
    },
    onError: (e) => toast.error(apiError(e, "Could not create course")),
  });

  const generate = useMutation({
    mutationFn: async (payload: AICoursePayload) =>
      (await api.post<CourseDetail>("/courses/generate", payload)).data,
    onSuccess: (course) => {
      toast.success("Course generated — review the material and generate the quiz");
      setAiDialogOpen(false);
      qc.invalidateQueries({ queryKey: ["courses"] });
      navigate(`/admin/courses/${course.id}`);
    },
    onError: (e) => toast.error(apiError(e, "Could not generate course")),
  });

  return (
    <div>
      <PageHeader
        title="Courses"
        description="Create courses, upload training material and publish"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setAiDialogOpen(true)}>
              <Sparkles className="h-4 w-4" /> Generate with AI
            </Button>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" /> Create course
            </Button>
          </div>
        }
      />

      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1 sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search courses…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            setStatusFilter(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="sm:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="published">Published</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="flex justify-center p-16">
          <Spinner className="h-6 w-6" />
        </div>
      ) : data?.items.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center text-muted-foreground">
            <BookOpen className="h-10 w-10 opacity-40" />
            <p>No courses yet. Create your first course to get started.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data?.items.map((c) => (
            <Link key={c.id} to={`/admin/courses/${c.id}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="flex h-full flex-col gap-3 p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <BookOpen className="h-5 w-5" />
                    </div>
                    <CourseStatusBadge status={c.status} expired={c.is_expired} />
                  </div>
                  <div className="flex-1">
                    <h3 className="line-clamp-1 font-semibold">{c.name}</h3>
                    <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                      {c.description || "No description"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <CourseTypeBadge type={c.course_type} />
                    {c.category && (
                      <span className="text-xs text-muted-foreground">{c.category}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 border-t pt-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <FileText className="h-3.5 w-3.5" /> {c.document_count} files
                    </span>
                    <span className="flex items-center gap-1">
                      <HelpCircle className="h-3.5 w-3.5" /> {c.quiz_question_count} Qs
                    </span>
                    <span>Pass {c.passing_percentage}%</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {data && data.total > PAGE_SIZE && (
        <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPage={setPage} />
      )}

      <CourseFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={(p) => create.mutate(p)}
        submitting={create.isPending}
      />

      <AICourseDialog
        open={aiDialogOpen}
        onOpenChange={setAiDialogOpen}
        onSubmit={(p) => generate.mutate(p)}
        submitting={generate.isPending}
      />
    </div>
  );
}
