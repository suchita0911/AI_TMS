"""Create in-app notifications and (optionally) send email (Phase 8)."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.course import Course, EmployeeCourseStatus
from app.models.enums import EnrollmentStatus
from app.models.notification import Notification
from app.models.user import User
from app.utils import email


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    def _create(self, *, user: User, ntype: str, title: str, message: str,
                course_id: int | None = None, send_email: bool = True) -> Notification:
        status = "none"
        if send_email and user.email:
            html = f"<h2>{title}</h2><p>{message}</p>"
            status = email.send_email(user.email, title, html, message)
        notif = Notification(
            user_id=user.id, course_id=course_id, type=ntype, title=title,
            message=message, channel="email" if send_email else "in_app",
            email_status=status,
        )
        self.db.add(notif)
        return notif

    def _course_link(self, course_id: int) -> str:
        return f"{settings.FRONTEND_BASE_URL}/my-courses/{course_id}"

    # ------------------------- Event triggers ------------------------- #
    def notify_assigned(self, course: Course, users: list[User]) -> int:
        for user in users:
            kind = "Mandatory" if course.course_type.value == "mandatory" else "Optional"
            due = f" Due by {course.end_date}." if course.end_date else ""
            self._create(
                user=user, ntype="assigned", course_id=course.id,
                title=f"New course assigned: {course.name}",
                message=(
                    f"You have been assigned the {kind.lower()} course '{course.name}'. "
                    f"{course.description or ''}{due} Open it here: {self._course_link(course.id)}"
                ),
            )
        self.db.commit()
        return len(users)

    def notify_published(self, course: Course) -> int:
        enrolled = self.db.execute(
            select(User).join(EmployeeCourseStatus, EmployeeCourseStatus.user_id == User.id)
            .where(EmployeeCourseStatus.course_id == course.id)
        ).scalars().all()
        for user in enrolled:
            self._create(
                user=user, ntype="published", course_id=course.id,
                title=f"Course available: {course.name}",
                message=f"The course '{course.name}' is now published and ready to start. "
                        f"{self._course_link(course.id)}",
            )
        self.db.commit()
        return len(enrolled)

    def notify_result(self, user: User, course: Course, passed: bool, score: float) -> None:
        if passed:
            title = f"Course completed: {course.name}"
            msg = (
                f"Congratulations! You passed '{course.name}' with a score of {score}% "
                f"(pass mark {course.passing_percentage}%)."
            )
        else:
            title = f"Quiz not passed: {course.name}"
            msg = f"You scored {score}% on '{course.name}' (pass mark {course.passing_percentage}%)."
        self._create(user=user, ntype="result", course_id=course.id, title=title,
                     message=msg, send_email=False)
        self.db.commit()

    # --------------------------- Reminders ---------------------------- #
    def generate_reminders(self) -> dict:
        """Create reminder notifications based on each enrollment's due date.

        Runs idempotently per day: skips if an equivalent reminder for the same
        course+user+bucket already exists today.
        """
        today = date.today()
        # Days-before-due → human phrase. Reminders go out in the run-up to the
        # due date only (5 days before is the main "about to expire" warning).
        buckets = {5: "in 5 days", 3: "in 3 days", 1: "tomorrow", 0: "today"}
        created = 0

        rows = self.db.execute(
            select(EmployeeCourseStatus, Course, User)
            .join(Course, Course.id == EmployeeCourseStatus.course_id)
            .join(User, User.id == EmployeeCourseStatus.user_id)
            .where(
                EmployeeCourseStatus.status != EnrollmentStatus.COMPLETED,
                Course.end_date.is_not(None),
            )
        ).all()

        for enrollment, course, user in rows:
            days_left = (course.end_date - today).days
            # Only remind BEFORE the due date. Once a course has expired the
            # employee can no longer start/resume/take it, so we do not send an
            # "expired/overdue" email — that would ask them to do the impossible.
            if days_left not in buckets:
                continue
            phrase = f"is due to expire {buckets[days_left]}"

            if self._reminder_exists_today(user.id, course.id, "reminder"):
                continue
            self._create(
                user=user, ntype="reminder", course_id=course.id,
                title=f"Reminder: {course.name} {phrase}",
                message=(
                    f"Your course '{course.name}' {phrase} (due {course.end_date}). "
                    f"Please complete it before the deadline. "
                    f"Open it here: {self._course_link(course.id)}"
                ),
            )
            created += 1
        self.db.commit()
        return {"reminders_created": created, "checked": len(rows)}

    def _reminder_exists_today(self, user_id: int, course_id: int, ntype: str) -> bool:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        existing = self.db.execute(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.course_id == course_id,
                Notification.type == ntype,
                Notification.created_at >= start,
            )
        ).first()
        return existing is not None

    # ------------------------- Employee inbox ------------------------- #
    def list_for(self, user: User, unread_only: bool = False, limit: int = 50) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user.id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def unread_count(self, user: User) -> int:
        return self.db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id, Notification.is_read.is_(False)
            )
        ) or 0

    def mark_read(self, notif_id: int, user: User) -> None:
        notif = self.db.get(Notification, notif_id)
        if not notif or notif.user_id != user.id:
            raise NotFoundError("Notification not found")
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        self.db.commit()

    def mark_all_read(self, user: User) -> int:
        rows = self.db.execute(
            select(Notification).where(
                Notification.user_id == user.id, Notification.is_read.is_(False)
            )
        ).scalars().all()
        now = datetime.now(timezone.utc)
        for n in rows:
            n.is_read = True
            n.read_at = now
        self.db.commit()
        return len(rows)
