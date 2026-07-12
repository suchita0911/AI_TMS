"""Reporting & analytics aggregations (Phase 7)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Numeric, case, cast, func, select
from sqlalchemy.orm import Session

from app.models.course import Course, EmployeeCourseStatus
from app.models.enums import CourseStatus, EnrollmentStatus, RoleName
from app.models.question import QuizAttempt
from app.models.user import Department, User


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------ Overview -------------------------- #
    def overview(self) -> dict:
        db = self.db
        total_courses = db.scalar(select(func.count(Course.id))) or 0
        published = db.scalar(
            select(func.count(Course.id)).where(Course.status == CourseStatus.PUBLISHED)
        ) or 0

        def _enroll(status):
            return db.scalar(
                select(func.count(EmployeeCourseStatus.id)).where(
                    EmployeeCourseStatus.status == status
                )
            ) or 0

        total_enroll = db.scalar(select(func.count(EmployeeCourseStatus.id))) or 0
        completed = _enroll(EnrollmentStatus.COMPLETED)
        failed = _enroll(EnrollmentStatus.FAILED)
        not_started = _enroll(EnrollmentStatus.NOT_STARTED)
        in_progress = _enroll(EnrollmentStatus.IN_PROGRESS) + _enroll(EnrollmentStatus.QUIZ_PENDING)

        overdue = db.scalar(
            select(func.count(EmployeeCourseStatus.id))
            .join(Course, Course.id == EmployeeCourseStatus.course_id)
            .where(
                EmployeeCourseStatus.status != EnrollmentStatus.COMPLETED,
                Course.end_date.is_not(None),
                Course.end_date < date.today(),
            )
        ) or 0

        # Quiz attempt stats
        submitted = db.scalar(
            select(func.count(QuizAttempt.id)).where(QuizAttempt.submitted_at.is_not(None))
        ) or 0
        passed = db.scalar(
            select(func.count(QuizAttempt.id)).where(QuizAttempt.passed.is_(True))
        ) or 0
        avg_score = db.scalar(
            select(func.avg(QuizAttempt.score_percentage)).where(
                QuizAttempt.submitted_at.is_not(None)
            )
        )

        return {
            "total_courses": total_courses,
            "active_courses": published,
            "total_enrollments": total_enroll,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "not_started": not_started,
            "overdue": overdue,
            "completion_rate": round(completed / total_enroll * 100, 1) if total_enroll else 0.0,
            "average_score": round(float(avg_score), 1) if avg_score is not None else 0.0,
            "pass_percentage": round(passed / submitted * 100, 1) if submitted else 0.0,
            "fail_percentage": round((submitted - passed) / submitted * 100, 1) if submitted else 0.0,
        }

    # -------------------------- Department-wise ----------------------- #
    def department_completion(self) -> list[dict]:
        rows = self.db.execute(
            select(
                Department.name,
                func.count(EmployeeCourseStatus.id),
                func.sum(
                    case((EmployeeCourseStatus.status == EnrollmentStatus.COMPLETED, 1), else_=0)
                ),
            )
            .select_from(EmployeeCourseStatus)
            .join(User, User.id == EmployeeCourseStatus.user_id)
            .join(Department, Department.id == User.department_id)
            .group_by(Department.name)
            .order_by(Department.name)
        ).all()
        result = []
        for name, total, completed in rows:
            total = total or 0
            completed = completed or 0
            result.append({
                "department": name,
                "total": total,
                "completed": completed,
                "completion_rate": round(completed / total * 100, 1) if total else 0.0,
            })
        return result

    # --------------------------- Employee-wise ------------------------ #
    def employee_progress(self) -> list[dict]:
        rows = self.db.execute(
            select(
                User.id, User.first_name, User.last_name, User.email, Department.name,
                func.count(EmployeeCourseStatus.id),
                func.sum(
                    case((EmployeeCourseStatus.status == EnrollmentStatus.COMPLETED, 1), else_=0)
                ),
                func.avg(cast(EmployeeCourseStatus.best_score, Numeric)),
            )
            .select_from(User)
            .join(User.role)
            .outerjoin(Department, Department.id == User.department_id)
            .outerjoin(EmployeeCourseStatus, EmployeeCourseStatus.user_id == User.id)
            .where(User.role.has(name=RoleName.EMPLOYEE))
            .group_by(User.id, Department.name)
            .order_by(User.first_name)
        ).all()
        out = []
        for uid, fn, ln, email, dept, assigned, completed, avg in rows:
            assigned = assigned or 0
            completed = completed or 0
            out.append({
                "user_id": uid,
                "name": f"{fn} {ln}",
                "email": email,
                "department": dept,
                "assigned": assigned,
                "completed": completed,
                "completion_rate": round(completed / assigned * 100, 1) if assigned else 0.0,
                "average_score": round(float(avg), 1) if avg is not None else None,
            })
        return out

    # ------------------------- Completion trend ----------------------- #
    def completion_trend(self, months: int = 6) -> list[dict]:
        month_col = func.to_char(
            func.date_trunc("month", EmployeeCourseStatus.completed_at), "YYYY-MM"
        )
        rows = self.db.execute(
            select(month_col, func.count(EmployeeCourseStatus.id))
            .where(EmployeeCourseStatus.completed_at.is_not(None))
            .group_by(month_col)
            .order_by(month_col)
        ).all()
        return [{"month": m, "completed": n} for m, n in rows if m]

    # ------------------------- Employee's own ------------------------- #
    def my_report(self, user: User) -> dict:
        rows = self.db.execute(
            select(EmployeeCourseStatus).where(EmployeeCourseStatus.user_id == user.id)
        ).scalars().all()
        assigned = len(rows)
        completed = sum(1 for r in rows if r.status == EnrollmentStatus.COMPLETED)
        pending = assigned - completed
        scores = [float(r.best_score) for r in rows if r.best_score is not None]
        return {
            "assigned": assigned,
            "completed": completed,
            "pending": pending,
            "completion_rate": round(completed / assigned * 100, 1) if assigned else 0.0,
            "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        }
