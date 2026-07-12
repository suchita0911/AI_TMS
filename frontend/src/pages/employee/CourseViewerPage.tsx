import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Play,
  CheckCircle2,
  Download,
  FileText,
  FileImage,
  FileVideo,
  FileAudio,
  File as FileIcon,
  HelpCircle,
  Award,
  AlertTriangle,
  Link2,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import { CourseTypeBadge, EnrollmentStatusBadge } from "@/components/StatusBadge";
import { MediaPlayer } from "@/components/MediaPlayer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader, Spinner } from "@/components/ui/spinner";
import { api, apiError } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import type { CourseDetail, CourseDocument, MyCourse } from "@/types";

function fileIcon(type: string) {
  if (type === "image") return FileImage;
  if (type === "video") return FileVideo;
  if (type === "audio") return FileAudio;
  if (["pdf", "doc", "docx", "ppt", "pptx", "txt"].includes(type)) return FileText;
  return FileIcon;
}

export default function CourseViewerPage() {
  const { id } = useParams();
  const courseId = Number(id);
  const qc = useQueryClient();

  const detail = useQuery({
    queryKey: ["my-course", courseId],
    queryFn: async () => (await api.get<CourseDetail>(`/me/courses/${courseId}`)).data,
  });
  const progress = useQuery({
    queryKey: ["my-courses"],
    queryFn: async () => (await api.get<MyCourse[]>("/me/courses")).data,
  });

  const mine = useMemo(
    () => progress.data?.find((c) => c.course_id === courseId),
    [progress.data, courseId]
  );

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["my-courses"] });
    qc.invalidateQueries({ queryKey: ["my-course", courseId] });
  };

  const start = useMutation({
    mutationFn: async () => api.post(`/me/courses/${courseId}/start`),
    onSuccess: () => {
      toast.success("Course started");
      invalidate();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const complete = useMutation({
    mutationFn: async () =>
      (await api.post<MyCourse>(`/me/courses/${courseId}/complete-content`)).data,
    onSuccess: (updated) => {
      toast.success(
        updated?.status === "completed"
          ? "Course completed!"
          : "Content marked complete — quiz is now pending",
      );
      invalidate();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const download = async (doc: CourseDocument) => {
    try {
      const res = await api.get(`/me/courses/${courseId}/documents/${doc.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.original_filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(apiError(e, "Download failed"));
    }
  };

  if (detail.isLoading || !detail.data) return <PageLoader />;
  const course = detail.data;
  const status = mine?.status ?? "not_started";

  return (
    <div>
      <Link
        to="/my-courses"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to my courses
      </Link>

      <PageHeader
        title={course.name}
        description={course.description || undefined}
        actions={<EnrollmentStatusBadge status={status} />}
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Training material</CardTitle>
          </CardHeader>
          <CardContent>
            {status === "expired" ? (
              <div className="rounded-lg border border-dashed border-destructive/40 bg-destructive/5 p-8 text-center">
                <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-destructive" />
                <p className="text-sm font-medium text-destructive">
                  This course has expired.
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  The due date ({formatDate(course.end_date)}) has passed, so it can no longer
                  be taken. Contact your administrator if you still need to complete it.
                </p>
              </div>
            ) : status === "not_started" ? (
              <div className="rounded-lg border border-dashed p-8 text-center">
                <p className="mb-4 text-sm text-muted-foreground">
                  Start the course to access the training material.
                </p>
                <Button onClick={() => start.mutate()} disabled={start.isPending}>
                  {start.isPending ? <Spinner /> : <Play className="h-4 w-4" />} Start course
                </Button>
              </div>
            ) : course.documents.length === 0 ? (
              <p className="p-4 text-center text-sm text-muted-foreground">
                No material available.
              </p>
            ) : (
              <ul className="divide-y">
                {course.documents.map((doc) => {
                  const isMedia = doc.file_type === "video" || doc.file_type === "audio";
                  const inlinePlayable = isMedia && !doc.source_url;
                  const Icon = doc.source_url ? Link2 : fileIcon(doc.file_type);
                  return (
                    <li key={doc.id} className="py-3">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-muted text-muted-foreground">
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{doc.original_filename}</p>
                          {doc.source_url && (
                            <a
                              href={doc.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="block truncate text-xs text-primary hover:underline"
                            >
                              {doc.source_url}
                            </a>
                          )}
                        </div>
                        {doc.source_url ? (
                          <Button variant="outline" size="sm" asChild>
                            <a href={doc.source_url} target="_blank" rel="noreferrer">
                              <ExternalLink className="h-4 w-4" /> Open link
                            </a>
                          </Button>
                        ) : (
                          <Button variant="outline" size="sm" onClick={() => download(doc)}>
                            <Download className="h-4 w-4" /> {inlinePlayable ? "Download" : "Open"}
                          </Button>
                        )}
                      </div>
                      {inlinePlayable && (
                        <div className="mt-3">
                          <MediaPlayer
                            url={`/me/courses/${courseId}/documents/${doc.id}/download`}
                            kind={doc.file_type as "video" | "audio"}
                          />
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Your progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Type</span>
              <CourseTypeBadge type={course.course_type} />
            </div>
            {course.trainer && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Trainer</span>
                <span className="font-medium">{course.trainer}</span>
              </div>
            )}
            {course.has_quiz ? (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Passing score</span>
                <span className="font-medium">{course.passing_percentage}%</span>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Assessment</span>
                <span className="font-medium">No quiz</span>
              </div>
            )}
            {course.has_quiz && mine?.best_score != null && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Your best score</span>
                <span
                  className={cn(
                    "font-medium",
                    mine.best_score >= course.passing_percentage
                      ? "text-success"
                      : "text-destructive",
                  )}
                >
                  {mine.best_score}%
                </span>
              </div>
            )}
            {course.has_quiz && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Questions</span>
                <span className="font-medium">{course.quiz_question_count}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Due date</span>
              <span className="font-medium">{formatDate(course.end_date)}</span>
            </div>

            <div className="border-t pt-4">
              {status === "expired" && (
                <div className="flex items-center justify-center gap-2 rounded-md bg-destructive/10 py-2 text-center text-sm text-destructive">
                  <AlertTriangle className="h-4 w-4" /> Expired — you can no longer proceed
                </div>
              )}
              {status === "in_progress" && (
                <Button
                  className="w-full"
                  onClick={() => complete.mutate()}
                  disabled={complete.isPending}
                >
                  {complete.isPending ? <Spinner /> : <CheckCircle2 className="h-4 w-4" />}
                  {course.has_quiz ? "Mark content complete" : "Mark as complete"}
                </Button>
              )}
              {(status === "quiz_pending" || status === "failed") && (
                mine?.can_attempt_quiz ? (
                  <Button className="w-full" asChild>
                    <Link to={`/my-courses/${courseId}/quiz`}>
                      <HelpCircle className="h-4 w-4" />
                      {status === "failed" ? "Retry quiz" : "Take quiz"}
                    </Link>
                  </Button>
                ) : (
                  <div className="space-y-1">
                    <Button className="w-full" disabled>
                      <HelpCircle className="h-4 w-4" /> Retry quiz
                    </Button>
                    <p className="text-center text-xs text-destructive">
                      No attempts remaining ({mine?.attempts_used}/{mine?.max_attempts} used)
                    </p>
                  </div>
                )
              )}
              {status === "completed" && (
                <div className="space-y-2">
                  <div className="flex items-center justify-center gap-2 rounded-md bg-success/10 py-2 text-success">
                    <CheckCircle2 className="h-4 w-4" /> Course completed
                  </div>
                  <Button variant="outline" className="w-full" asChild>
                    <Link to={`/my-courses/${courseId}/certificate`}>
                      <Award className="h-4 w-4" /> View certificate
                    </Link>
                  </Button>
                </div>
              )}
              {status === "not_started" && (
                <p className="text-center text-xs text-muted-foreground">
                  Start the course to begin.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
