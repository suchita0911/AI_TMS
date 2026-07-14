import { useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Upload,
  Trash2,
  Download,
  Pencil,
  Send,
  Undo2,
  FileText,
  FileImage,
  FileVideo,
  FileAudio,
  File as FileIcon,
  Link2,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/PageHeader";
import {
  CourseStatusBadge,
  CourseTypeBadge,
  EnrollmentStatusBadge,
} from "@/components/StatusBadge";
import { CourseFormDialog } from "@/components/CourseFormDialog";
import { AssignDialog, type AssignPayload } from "@/components/AssignDialog";
import { QuestionBankCard } from "@/components/QuestionBankCard";
import { MediaPlayer } from "@/components/MediaPlayer";
import { UsersRound, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader, Spinner } from "@/components/ui/spinner";
import { api, apiError } from "@/lib/api";
import { notifyDeleted } from "@/lib/notify";
import { formatDate } from "@/lib/utils";
import type { CourseDetail, CourseDocument, Enrollment } from "@/types";

function fileIcon(type: string) {
  if (type === "image") return FileImage;
  if (type === "video") return FileVideo;
  if (type === "audio") return FileAudio;
  if (["pdf", "doc", "docx", "ppt", "pptx", "txt"].includes(type)) return FileText;
  return FileIcon;
}

function humanSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function CourseDetailPage() {
  const { id } = useParams();
  const courseId = Number(id);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [showLink, setShowLink] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");

  const { data: course, isLoading } = useQuery({
    queryKey: ["course", courseId],
    queryFn: async () => (await api.get<CourseDetail>(`/courses/${courseId}`)).data,
    // While any file is still being processed (e.g. audio/video transcription
    // running in the background), poll so the status updates on its own.
    refetchInterval: (query) =>
      query.state.data?.documents.some((d) => d.status === "processing") ? 4000 : false,
  });

  const enrollments = useQuery({
    queryKey: ["enrollments", courseId],
    queryFn: async () =>
      (await api.get<Enrollment[]>(`/courses/${courseId}/enrollments`)).data,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["course", courseId] });
    qc.invalidateQueries({ queryKey: ["courses"] });
  };
  const invalidateEnroll = () => qc.invalidateQueries({ queryKey: ["enrollments", courseId] });

  const assign = useMutation({
    mutationFn: async (p: AssignPayload) =>
      (await api.post(`/courses/${courseId}/assign`, p)).data,
    onSuccess: (data: any) => {
      toast.success(data.message ?? "Assigned");
      setAssignOpen(false);
      invalidateEnroll();
    },
    onError: (e) => toast.error(apiError(e, "Assignment failed")),
  });

  const unassign = useMutation({
    mutationFn: async (userId: number) =>
      api.delete(`/courses/${courseId}/enrollments/${userId}`),
    onSuccess: () => {
      toast.success("Employee unassigned");
      invalidateEnroll();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const edit = useMutation({
    mutationFn: async (payload: any) => api.patch(`/courses/${courseId}`, payload),
    onSuccess: () => {
      toast.success("Course updated");
      setEditOpen(false);
      invalidate();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post(`/courses/${courseId}/documents`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: () => {
      toast.success("Material uploaded");
      invalidate();
    },
    onError: (e) => toast.error(apiError(e, "Upload failed")),
  });

  const addLink = useMutation({
    mutationFn: async (url: string) => api.post(`/courses/${courseId}/link`, { url }),
    onSuccess: () => {
      toast.success("Link added — fetching content");
      setLinkUrl("");
      setShowLink(false);
      invalidate();
    },
    onError: (e) => toast.error(apiError(e, "Could not add link")),
  });

  const removeDoc = useMutation({
    mutationFn: async (docId: number) => api.delete(`/courses/${courseId}/documents/${docId}`),
    onSuccess: () => {
      notifyDeleted("Material");
      invalidate();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const publish = useMutation({
    mutationFn: async (action: "publish" | "unpublish") =>
      api.post(`/courses/${courseId}/${action}`),
    onSuccess: (_d, action) => {
      toast.success(action === "publish" ? "Course published" : "Course moved to draft");
      invalidate();
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const remove = useMutation({
    mutationFn: async () => api.delete(`/courses/${courseId}`),
    onSuccess: () => {
      notifyDeleted("Course", course?.name);
      navigate("/admin/courses");
    },
    onError: (e) => toast.error(apiError(e)),
  });

  const download = async (doc: CourseDocument) => {
    try {
      const res = await api.get(`/courses/${courseId}/documents/${doc.id}/download`, {
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

  if (isLoading || !course) return <PageLoader />;

  return (
    <div>
      <Link
        to="/admin/courses"
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Back to courses
      </Link>

      <PageHeader
        title={course.name}
        description={course.description || undefined}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={() => setEditOpen(true)}>
              <Pencil className="h-4 w-4" /> Edit
            </Button>
            {course.status === "published" ? (
              <Button variant="outline" onClick={() => publish.mutate("unpublish")} disabled={publish.isPending}>
                <Undo2 className="h-4 w-4" /> Unpublish
              </Button>
            ) : (
              <Button onClick={() => publish.mutate("publish")} disabled={publish.isPending}>
                {publish.isPending ? <Spinner /> : <Send className="h-4 w-4" />} Publish
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="text-destructive"
              onClick={() => {
                if (confirm(`Delete course "${course.name}"? This cannot be undone.`)) remove.mutate();
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        }
      />

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Details */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Status"><CourseStatusBadge status={course.status} expired={course.is_expired} /></Row>
            <Row label="Type"><CourseTypeBadge type={course.course_type} /></Row>
            <Row label="Category">{course.category || "—"}</Row>
            <Row label="Trainer">{course.trainer || "—"}</Row>
            <Row label="Start date">{formatDate(course.start_date)}</Row>
            <Row label="End date">{formatDate(course.end_date)}</Row>
            <Row label="Quiz">{course.has_quiz ? "Yes" : "No quiz"}</Row>
            {course.has_quiz && (
              <>
                <Row label="Passing %">{course.passing_percentage}%</Row>
                <Row label="Quiz questions">{course.quiz_question_count}</Row>
                <Row label="Retry">{course.allow_retry ? `Up to ${course.retry_count}` : "Not allowed"}</Row>
              </>
            )}
          </CardContent>
        </Card>

        {/* Materials */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">Training material ({course.documents.length})</CardTitle>
            <div className="flex gap-2">
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) upload.mutate(f);
                  e.target.value = "";
                }}
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowLink((s) => !s)}
                disabled={addLink.isPending}
              >
                <Link2 className="h-4 w-4" /> Add link
              </Button>
              <Button size="sm" onClick={() => fileRef.current?.click()} disabled={upload.isPending}>
                {upload.isPending ? <Spinner /> : <Upload className="h-4 w-4" />} Upload
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {showLink && (
              <div className="mb-4 flex flex-col gap-2 rounded-lg border bg-muted/30 p-3 sm:flex-row">
                <Input
                  autoFocus
                  placeholder="https://example.com/article  or  https://…/lecture.mp4"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && linkUrl.trim()) addLink.mutate(linkUrl.trim());
                  }}
                />
                <Button
                  size="sm"
                  onClick={() => linkUrl.trim() && addLink.mutate(linkUrl.trim())}
                  disabled={addLink.isPending || !linkUrl.trim()}
                >
                  {addLink.isPending ? <Spinner /> : <Link2 className="h-4 w-4" />} Add
                </Button>
              </div>
            )}
            {course.documents.length === 0 ? (
              <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                No material uploaded yet. Supported: PDF, DOC, DOCX, PPT, PPTX, TXT, images,
                audio and video. Add at least one file before publishing.
              </div>
            ) : (
              <ul className="divide-y">
                {course.documents.map((doc) => {
                  const isMedia = doc.file_type === "video" || doc.file_type === "audio";
                  const inlinePlayable = isMedia && !doc.source_url && doc.status !== "processing";
                  const Icon = doc.source_url ? Link2 : fileIcon(doc.file_type);
                  return (
                    <li key={doc.id} className="flex flex-col py-3">
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
                        <p className="text-xs text-muted-foreground">
                          {(doc.source_url ? "LINK" : doc.file_type.toUpperCase())}
                          {!doc.source_url && ` · ${humanSize(doc.size_bytes)}`}
                          {doc.status === "processing" && (
                            <span className="text-warning"> · transcribing / extracting…</span>
                          )}
                          {doc.status === "failed" && (
                            <span className="text-destructive"> · extraction failed</span>
                          )}
                        </p>
                      </div>
                      {doc.source_url ? (
                        <Button variant="ghost" size="icon" asChild>
                          <a href={doc.source_url} target="_blank" rel="noreferrer" aria-label="Open link">
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        </Button>
                      ) : (
                        <Button variant="ghost" size="icon" onClick={() => download(doc)}>
                          <Download className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        onClick={() => removeDoc.mutate(doc.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                      </div>
                      {inlinePlayable && (
                        <div className="mt-3 pl-12">
                          <MediaPlayer
                            url={`/courses/${courseId}/documents/${doc.id}/download`}
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
      </div>

      {/* AI question bank — only for courses that have a quiz */}
      {course.has_quiz && <QuestionBankCard courseId={courseId} />}

      {/* Assigned employees */}
      <Card className="mt-5">
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base">
              Assigned employees ({enrollments.data?.length ?? 0})
            </CardTitle>
            {course.course_type === "mandatory" && (
              <p className="mt-1 text-xs text-muted-foreground">
                Mandatory course — auto-assigned to all employees on publish and to anyone added later.
              </p>
            )}
          </div>
          <Button size="sm" onClick={() => setAssignOpen(true)}>
            <UsersRound className="h-4 w-4" /> Assign
          </Button>
        </CardHeader>
        <CardContent>
          {enrollments.isLoading ? (
            <div className="flex justify-center p-6">
              <Spinner />
            </div>
          ) : enrollments.data && enrollments.data.length > 0 ? (
            <ul className="divide-y">
              {enrollments.data.map((e) => (
                <li key={e.id} className="flex items-center gap-3 py-3">
                  <div className="min-w-0 flex-1">
                    <Link
                      to={`/admin/employees/${e.user.id}`}
                      className="truncate text-sm font-medium text-primary hover:underline"
                    >
                      {e.user.first_name} {e.user.last_name}
                    </Link>
                    <p className="text-xs text-muted-foreground">
                      {e.user.email} · {e.user.department ?? "No department"}
                    </p>
                  </div>
                  {e.best_score != null && (
                    <span className="text-xs text-muted-foreground">{e.best_score}%</span>
                  )}
                  <EnrollmentStatusBadge status={e.status} />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive"
                    title="Unassign"
                    onClick={() => unassign.mutate(e.user.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              No one is assigned yet. Use <b>Assign</b> to target all employees, a department,
              a group, or specific people.
            </div>
          )}
        </CardContent>
      </Card>

      <CourseFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        initial={course}
        onSubmit={(p) => edit.mutate(p)}
        submitting={edit.isPending}
      />
      <AssignDialog
        open={assignOpen}
        onOpenChange={setAssignOpen}
        onAssign={(p) => assign.mutate(p)}
        submitting={assign.isPending}
      />
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{children}</span>
    </div>
  );
}
