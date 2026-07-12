"""Data access for course assignments and per-employee enrollment status."""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Course, CourseAssignment, EmployeeCourseStatus
from app.models.enums import EnrollmentStatus
from app.repositories.base import BaseRepository


class EnrollmentRepository(BaseRepository[EmployeeCourseStatus]):
    model = EmployeeCourseStatus

    def get_for(self, course_id: int, user_id: int) -> Optional[EmployeeCourseStatus]:
        return self.db.execute(
            select(EmployeeCourseStatus).where(
                EmployeeCourseStatus.course_id == course_id,
                EmployeeCourseStatus.user_id == user_id,
            )
        ).scalar_one_or_none()

    def existing_user_ids(self, course_id: int) -> set[int]:
        rows = self.db.execute(
            select(EmployeeCourseStatus.user_id).where(
                EmployeeCourseStatus.course_id == course_id
            )
        ).scalars().all()
        return set(rows)

    def for_course(self, course_id: int) -> Sequence[EmployeeCourseStatus]:
        return (
            self.db.execute(
                select(EmployeeCourseStatus)
                .options(selectinload(EmployeeCourseStatus.user))
                .where(EmployeeCourseStatus.course_id == course_id)
                .order_by(EmployeeCourseStatus.created_at.desc())
            )
            .scalars()
            .all()
        )

    def for_user(self, user_id: int) -> Sequence[EmployeeCourseStatus]:
        """Enrollments joined to their (published) course, for an employee."""
        return (
            self.db.execute(
                select(EmployeeCourseStatus)
                .options(selectinload(EmployeeCourseStatus.course).selectinload(Course.documents))
                .where(EmployeeCourseStatus.user_id == user_id)
                .order_by(EmployeeCourseStatus.assigned_at.desc())
            )
            .scalars()
            .all()
        )

    def count_by_status(self, course_id: int) -> dict[str, int]:
        rows = self.db.execute(
            select(EmployeeCourseStatus.status, func.count())
            .where(EmployeeCourseStatus.course_id == course_id)
            .group_by(EmployeeCourseStatus.status)
        ).all()
        return {str(status.value if hasattr(status, "value") else status): n for status, n in rows}


class CourseAssignmentRepository(BaseRepository[CourseAssignment]):
    model = CourseAssignment
