import { Badge } from "@/components/ui/badge";
import type { CourseStatus, CourseType, EnrollmentStatus, UserStatus } from "@/types";

const STATUS: Record<UserStatus, { label: string; variant: "success" | "warning" | "secondary" }> = {
  active: { label: "Active", variant: "success" },
  pending: { label: "Pending", variant: "warning" },
  inactive: { label: "Inactive", variant: "secondary" },
};

export function UserStatusBadge({ status }: { status: UserStatus }) {
  const cfg = STATUS[status];
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

const COURSE_STATUS: Record<
  CourseStatus,
  { label: string; variant: "success" | "warning" | "secondary" }
> = {
  draft: { label: "Draft", variant: "warning" },
  published: { label: "Published", variant: "success" },
  archived: { label: "Archived", variant: "secondary" },
};

export function CourseStatusBadge({
  status,
  expired = false,
}: {
  status: CourseStatus;
  expired?: boolean;
}) {
  // A published course past its due date is shown as "Expired" rather than
  // "Published" so admins can see it is no longer being taken/assigned.
  if (expired && status === "published") {
    return <Badge variant="destructive">Expired</Badge>;
  }
  const cfg = COURSE_STATUS[status];
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

export function CourseTypeBadge({ type }: { type: CourseType }) {
  return (
    <Badge variant={type === "mandatory" ? "destructive" : "secondary"}>
      {type === "mandatory" ? "Mandatory" : "Optional"}
    </Badge>
  );
}

const ENROLLMENT: Record<
  EnrollmentStatus,
  { label: string; variant: "default" | "success" | "warning" | "secondary" | "destructive" }
> = {
  not_started: { label: "Not Started", variant: "secondary" },
  in_progress: { label: "In Progress", variant: "default" },
  quiz_pending: { label: "Quiz Pending", variant: "warning" },
  completed: { label: "Completed", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  overdue: { label: "Overdue", variant: "destructive" },
  expired: { label: "Expired", variant: "destructive" },
};

export function EnrollmentStatusBadge({ status }: { status: EnrollmentStatus }) {
  const cfg = ENROLLMENT[status];
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}
