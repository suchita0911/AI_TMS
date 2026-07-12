"""Course assignment & employee enrollment/progress business logic."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.models.course import Course, CourseAssignment, EmployeeCourseStatus
from app.models.enums import (
    AssignmentTargetType,
    CourseStatus,
    CourseType,
    EnrollmentStatus,
)
from app.models.user import Group, User, group_members
from app.repositories.course_repository import CourseRepository
from app.repositories.enrollment_repository import (
    CourseAssignmentRepository,
    EnrollmentRepository,
)
from app.repositories.user_repository import (
    DepartmentRepository,
    GroupRepository,
    UserRepository,
)
from app.schemas.assignment import AssignRequest
from app.services.audit_service import AuditService


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.courses = CourseRepository(db)
        self.enrollments = EnrollmentRepository(db)
        self.assignments = CourseAssignmentRepository(db)
        self.users = UserRepository(db)
        self.departments = DepartmentRepository(db)
        self.groups = GroupRepository(db)
        self.audit = AuditService(db)

    def _get_course(self, course_id: int) -> Course:
        course = self.courses.get(course_id)
        if not course:
            raise NotFoundError("Course not found")
        return course

    # ------------------------- Target resolution ------------------------- #
    def _resolve_targets(self, data: AssignRequest) -> list[User]:
        """Return the active users a target expands to.

        Course assignment is role-agnostic: admins take assigned/mandatory
        training the same as everyone else, so no role filtering is applied.
        """
        if data.target_type == AssignmentTargetType.ALL:
            stmt = select(User).where(User.is_active.is_(True))
            return list(self.db.execute(stmt).scalars().all())

        if data.target_type == AssignmentTargetType.DEPARTMENT:
            if not self.departments.get(data.department_id):
                raise NotFoundError("Department not found")
            users = self.users.get_by_department(data.department_id)
            return [u for u in users if u.is_active]

        if data.target_type == AssignmentTargetType.GROUP:
            group = self.groups.get(data.group_id)
            if not group:
                raise NotFoundError("Group not found")
            return [u for u in group.members if u.is_active]

        # INDIVIDUAL (one or many explicit users)
        users = self.db.execute(
            select(User).where(User.id.in_(data.user_ids))
        ).scalars().all()
        found = list(users)
        if not found:
            raise BusinessRuleError("No valid users found in the selection")
        return found

    # ------------------------------- Assign ------------------------------- #
    def assign(self, course_id: int, data: AssignRequest, actor: User) -> dict:
        course = self._get_course(course_id)
        targets = self._resolve_targets(data)
        existing = self.enrollments.existing_user_ids(course_id)

        now = datetime.now(timezone.utc)
        assigned = 0
        newly_assigned: list[User] = []
        for user in targets:
            if user.id in existing:
                continue
            self.db.add(
                EmployeeCourseStatus(
                    course_id=course_id,
                    user_id=user.id,
                    status=EnrollmentStatus.NOT_STARTED,
                    assigned_at=now,
                )
            )
            newly_assigned.append(user)
            assigned += 1

        self.assignments.add(
            CourseAssignment(
                course_id=course_id,
                target_type=data.target_type,
                department_id=data.department_id,
                group_id=data.group_id,
                user_id=data.user_ids[0] if (
                    data.target_type == AssignmentTargetType.INDIVIDUAL
                    and len(data.user_ids) == 1
                ) else None,
                resolved_count=len(targets),
                assigned_by_id=actor.id,
            )
        )
        self.audit.record(action="course.assign", user_id=actor.id, entity_type="course",
                          entity_id=course_id,
                          detail=f"{data.target_type.value}: +{assigned} of {len(targets)}")
        self.db.flush()
        # Notify newly assigned employees (in-app + email if configured).
        if newly_assigned and course.status == CourseStatus.PUBLISHED:
            from app.services.notification_service import NotificationService
            NotificationService(self.db).notify_assigned(course, newly_assigned)
        self.db.commit()
        return {
            "assigned": assigned,
            "already_assigned": len(targets) - assigned,
            "total_targeted": len(targets),
            "message": f"Assigned to {assigned} new employee(s).",
        }

    # ------------------- Mandatory auto-assignment -------------------- #
    def _enroll_new(self, course: Course, users: list[User]) -> list[User]:
        """Create NOT_STARTED enrollments for users not already enrolled."""
        existing = self.enrollments.existing_user_ids(course.id)
        now = datetime.now(timezone.utc)
        newly: list[User] = []
        for user in users:
            if user.id in existing:
                continue
            self.db.add(
                EmployeeCourseStatus(
                    course_id=course.id, user_id=user.id,
                    status=EnrollmentStatus.NOT_STARTED, assigned_at=now,
                )
            )
            newly.append(user)
        return newly

    def assign_all_active_employees(self, course: Course, actor: User | None = None) -> int:
        """Assign a course to every active employee (used for mandatory courses)."""
        users = self._resolve_targets(AssignRequest(target_type=AssignmentTargetType.ALL))
        newly = self._enroll_new(course, users)
        if newly:
            self.db.add(CourseAssignment(
                course_id=course.id, target_type=AssignmentTargetType.ALL,
                resolved_count=len(users),
                assigned_by_id=actor.id if actor else None,
            ))
            self.db.flush()
            if course.status == CourseStatus.PUBLISHED:
                from app.services.notification_service import NotificationService
                NotificationService(self.db).notify_assigned(course, newly)
        self.db.commit()
        return len(newly)

    def assign_mandatory_courses_to_user(self, user: User) -> int:
        """Enroll a (new) user into every published mandatory course.

        Applies to all roles — admins complete mandatory training too.
        """
        courses = self.db.execute(
            select(Course).where(
                Course.status == CourseStatus.PUBLISHED,
                Course.course_type == CourseType.MANDATORY,
            )
        ).scalars().all()
        count = 0
        for course in courses:
            if course.is_expired:
                continue  # don't hand a newly added employee an already-expired course
            if self.enrollments.get_for(course.id, user.id):
                continue
            self.db.add(EmployeeCourseStatus(
                course_id=course.id, user_id=user.id,
                status=EnrollmentStatus.NOT_STARTED,
                assigned_at=datetime.now(timezone.utc),
            ))
            self.db.flush()
            from app.services.notification_service import NotificationService
            NotificationService(self.db).notify_assigned(course, [user])
            count += 1
        self.db.commit()
        return count

    def list_enrollments(self, course_id: int) -> list[EmployeeCourseStatus]:
        self._get_course(course_id)
        return list(self.enrollments.for_course(course_id))

    def unassign(self, course_id: int, user_id: int, actor: User) -> None:
        enrollment = self.enrollments.get_for(course_id, user_id)
        if not enrollment:
            raise NotFoundError("Enrollment not found")
        self.enrollments.delete(enrollment)
        self.audit.record(action="course.unassign", user_id=actor.id, entity_type="course",
                          entity_id=course_id, detail=f"user {user_id}")
        self.db.commit()

    # -------------------------- Employee actions -------------------------- #
    @staticmethod
    def _is_expired(enrollment: EmployeeCourseStatus, course: Course) -> bool:
        """A course the employee hasn't completed and whose due date has passed."""
        if enrollment.status == EnrollmentStatus.COMPLETED:
            return False
        return course.is_expired

    def my_courses(self, user: User) -> list[dict]:
        rows = self.enrollments.for_user(user.id)
        result: list[dict] = []
        for e in rows:
            course = e.course
            if course.status != CourseStatus.PUBLISHED:
                continue  # employees only see published assigned courses
            expired = self._is_expired(e, course)
            max_attempts = (1 + course.retry_count) if course.allow_retry else 1
            can_attempt = (
                course.has_quiz
                and not expired
                and e.status != EnrollmentStatus.COMPLETED
                and e.attempts_used < max_attempts
            )
            result.append(
                {
                    "course_id": course.id,
                    "name": course.name,
                    "description": course.description,
                    "category": course.category,
                    "course_type": course.course_type,
                    "start_date": course.start_date,
                    "end_date": course.end_date,
                    "has_quiz": course.has_quiz,
                    "passing_percentage": course.passing_percentage,
                    "quiz_question_count": course.quiz_question_count,
                    "document_count": len(course.documents),
                    "status": EnrollmentStatus.EXPIRED if expired else e.status,
                    "best_score": float(e.best_score) if e.best_score is not None else None,
                    "attempts_used": e.attempts_used,
                    "max_attempts": max_attempts,
                    "can_attempt_quiz": can_attempt,
                    "started_at": e.started_at,
                    "completed_at": e.completed_at,
                    # ``is_overdue`` is kept for the admin dashboards/reports that
                    # count past-due enrollments; it mirrors the expired state.
                    "is_overdue": expired,
                }
            )
        return result

    def _my_enrollment(self, course_id: int, user: User) -> tuple[EmployeeCourseStatus, Course]:
        enrollment = self.enrollments.get_for(course_id, user.id)
        if not enrollment:
            raise PermissionDeniedError("This course is not assigned to you")
        course = self.courses.get_with_documents(course_id)
        if not course or course.status != CourseStatus.PUBLISHED:
            raise NotFoundError("Course not available")
        return enrollment, course

    def get_my_course(self, course_id: int, user: User) -> tuple[EmployeeCourseStatus, Course]:
        return self._my_enrollment(course_id, user)

    def start_course(self, course_id: int, user: User) -> EmployeeCourseStatus:
        enrollment, course = self._my_enrollment(course_id, user)
        if self._is_expired(enrollment, course):
            raise BusinessRuleError(
                "This course has expired and can no longer be started."
            )
        if enrollment.status == EnrollmentStatus.NOT_STARTED:
            enrollment.status = EnrollmentStatus.IN_PROGRESS
            enrollment.started_at = datetime.now(timezone.utc)
            self.db.commit()
        return enrollment

    def complete_content(self, course_id: int, user: User) -> EmployeeCourseStatus:
        enrollment, course = self._my_enrollment(course_id, user)
        if self._is_expired(enrollment, course):
            raise BusinessRuleError(
                "This course has expired and can no longer be taken."
            )
        if enrollment.status in (EnrollmentStatus.NOT_STARTED, EnrollmentStatus.IN_PROGRESS):
            now = datetime.now(timezone.utc)
            enrollment.content_completed_at = now
            if not enrollment.started_at:
                enrollment.started_at = now
            if course.has_quiz:
                enrollment.status = EnrollmentStatus.QUIZ_PENDING
            else:
                # No quiz: finishing the material completes the course.
                enrollment.status = EnrollmentStatus.COMPLETED
                enrollment.completed_at = now
                self.db.flush()
                from app.services.notification_service import NotificationService
                NotificationService(self.db).notify_result(user, course, True, 100.0)
            self.db.commit()
        return enrollment
