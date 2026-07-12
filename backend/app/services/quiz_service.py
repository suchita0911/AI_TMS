"""Quiz engine: build randomized quizzes, evaluate, and update course status."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.models.course import Course, EmployeeCourseStatus
from app.models.enums import (
    CourseStatus,
    DifficultyLevel,
    EnrollmentStatus,
    QuizAttemptStatus,
)
from app.models.question import QuestionBank, QuizAnswer, QuizAttempt
from app.models.user import User
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.question_repository import QuestionBankRepository
from app.services.audit_service import AuditService

# Target difficulty ratio (spec example: 4 easy / 4 medium / 2 hard for 10 Qs).
_RATIO = [
    (DifficultyLevel.EASY, 0.4),
    (DifficultyLevel.MEDIUM, 0.4),
    (DifficultyLevel.HARD, 0.2),
]


def compute_distribution(total: int, available: dict[DifficultyLevel, int]) -> dict[DifficultyLevel, int]:
    """Fixed difficulty distribution for everyone, capped by availability.

    Guarantees the same difficulty mix for every employee; only the specific
    questions differ. Falls back to filling from other buckets if one is short.
    """
    plan: dict[DifficultyLevel, int] = {}
    for level, ratio in _RATIO:
        plan[level] = min(round(total * ratio), available.get(level, 0))

    # Fill any shortfall (rounding or scarce buckets) from remaining capacity.
    def _short() -> int:
        return total - sum(plan.values())

    order = [DifficultyLevel.MEDIUM, DifficultyLevel.EASY, DifficultyLevel.HARD]
    i = 0
    while _short() > 0 and i < 100:
        level = order[i % len(order)]
        if plan[level] < available.get(level, 0):
            plan[level] += 1
        elif all(plan[l] >= available.get(l, 0) for l in plan):
            break
        i += 1
    return plan


class QuizService:
    def __init__(self, db: Session):
        self.db = db
        self.questions = QuestionBankRepository(db)
        self.enrollments = EnrollmentRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ #
    def _enrollment(self, course_id: int, user: User) -> tuple[EmployeeCourseStatus, Course]:
        enrollment = self.enrollments.get_for(course_id, user.id)
        if not enrollment:
            raise PermissionDeniedError("This course is not assigned to you")
        course = self.db.get(Course, course_id)
        if not course or course.status != CourseStatus.PUBLISHED:
            raise NotFoundError("Course not available")
        return enrollment, course

    @staticmethod
    def _max_attempts(course: Course) -> int:
        return (1 + course.retry_count) if course.allow_retry else 1

    def _active_attempt(self, course_id: int, user_id: int) -> QuizAttempt | None:
        return self.db.execute(
            select(QuizAttempt).where(
                QuizAttempt.course_id == course_id,
                QuizAttempt.user_id == user_id,
                QuizAttempt.status == QuizAttemptStatus.IN_PROGRESS,
            )
        ).scalar_one_or_none()

    # ------------------------------- Start ---------------------------- #
    def start(self, course_id: int, user: User) -> QuizAttempt:
        enrollment, course = self._enrollment(course_id, user)

        if not course.has_quiz:
            raise BusinessRuleError("This course does not have a quiz.")

        if enrollment.status == EnrollmentStatus.COMPLETED:
            raise BusinessRuleError("You have already completed this course")

        if course.is_expired:
            raise BusinessRuleError(
                "This course has expired and the quiz can no longer be taken."
            )

        # Resume an in-progress attempt instead of creating a duplicate.
        existing = self._active_attempt(course_id, user.id)
        if existing:
            return existing

        if enrollment.status not in (
            EnrollmentStatus.QUIZ_PENDING,
            EnrollmentStatus.IN_PROGRESS,
            EnrollmentStatus.FAILED,
            EnrollmentStatus.NOT_STARTED,
        ):
            raise BusinessRuleError("Quiz is not available in the current course state")

        max_attempts = self._max_attempts(course)
        if enrollment.attempts_used >= max_attempts:
            raise BusinessRuleError("No quiz attempts remaining")

        pool = list(self.questions.all_active(course_id))
        if not pool:
            raise BusinessRuleError("No questions available. Ask an admin to generate the quiz.")

        by_diff: dict[DifficultyLevel, list[QuestionBank]] = {
            DifficultyLevel.EASY: [], DifficultyLevel.MEDIUM: [], DifficultyLevel.HARD: [],
        }
        for q in pool:
            by_diff.setdefault(q.difficulty, []).append(q)

        available = {lvl: len(qs) for lvl, qs in by_diff.items()}
        target = min(course.quiz_question_count, len(pool))
        plan = compute_distribution(target, available)

        # Randomly sample DIFFERENT questions per employee within each bucket.
        selected: list[QuestionBank] = []
        for level, n in plan.items():
            bucket = by_diff.get(level, [])
            random.shuffle(bucket)
            selected.extend(bucket[:n])

        random.shuffle(selected)  # randomize question order

        attempt = QuizAttempt(
            course_id=course_id,
            user_id=user.id,
            attempt_number=enrollment.attempts_used + 1,
            status=QuizAttemptStatus.IN_PROGRESS,
            total_questions=len(selected),
            passing_percentage=course.passing_percentage,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(attempt)
        self.db.flush()

        for order, q in enumerate(selected):
            opts = list(q.options)
            random.shuffle(opts)  # shuffle answer options
            self.db.add(
                QuizAnswer(
                    attempt_id=attempt.id,
                    question_id=q.id,
                    display_order=order,
                    presented_options=opts,
                    correct_answer=q.correct_answer,
                )
            )

        if enrollment.status == EnrollmentStatus.NOT_STARTED:
            enrollment.status = EnrollmentStatus.IN_PROGRESS
        self.audit.record(action="quiz.start", user_id=user.id, entity_type="quiz_attempt",
                          entity_id=attempt.id, detail=f"course {course_id}")
        self.db.commit()
        return attempt

    # ------------------------------- Read ----------------------------- #
    def get_attempt(self, attempt_id: int, user: User) -> QuizAttempt:
        attempt = self.db.execute(
            select(QuizAttempt)
            .options(selectinload(QuizAttempt.answers).selectinload(QuizAnswer.question))
            .where(QuizAttempt.id == attempt_id)
        ).scalar_one_or_none()
        if not attempt:
            raise NotFoundError("Quiz attempt not found")
        if attempt.user_id != user.id:
            raise PermissionDeniedError("Not your quiz attempt")
        return attempt

    def history(self, course_id: int, user: User) -> list[QuizAttempt]:
        return list(
            self.db.execute(
                select(QuizAttempt)
                .where(QuizAttempt.course_id == course_id, QuizAttempt.user_id == user.id)
                .order_by(QuizAttempt.attempt_number.desc())
            ).scalars().all()
        )

    # ------------------------------ Submit ---------------------------- #
    def submit(self, attempt_id: int, answers: list, user: User) -> QuizAttempt:
        attempt = self.get_attempt(attempt_id, user)
        if attempt.status != QuizAttemptStatus.IN_PROGRESS:
            raise BusinessRuleError("This quiz has already been submitted")

        selection = {a.answer_id: (a.selected or "") for a in answers}
        correct = 0
        for ans in attempt.answers:
            chosen = selection.get(ans.id)
            ans.selected_answer = chosen
            ans.is_correct = (
                chosen is not None
                and chosen.strip().lower() == ans.correct_answer.strip().lower()
            )
            if ans.is_correct:
                correct += 1

        total = attempt.total_questions or len(attempt.answers)
        score = round((correct / total) * 100, 2) if total else 0.0
        passed = score >= attempt.passing_percentage

        attempt.correct_count = correct
        attempt.score_percentage = score
        attempt.passed = passed
        attempt.status = QuizAttemptStatus.PASSED if passed else QuizAttemptStatus.FAILED
        attempt.submitted_at = datetime.now(timezone.utc)

        # Update the enrollment / course status.
        enrollment, course = self._enrollment(attempt.course_id, user)
        enrollment.attempts_used += 1
        if enrollment.best_score is None or score > float(enrollment.best_score):
            enrollment.best_score = score
        if passed:
            enrollment.status = EnrollmentStatus.COMPLETED
            enrollment.completed_at = datetime.now(timezone.utc)
        else:
            enrollment.status = EnrollmentStatus.FAILED

        self.audit.record(action="quiz.submit", user_id=user.id, entity_type="quiz_attempt",
                          entity_id=attempt.id,
                          detail=f"score={score} passed={passed}")
        self.db.flush()
        from app.services.notification_service import NotificationService
        NotificationService(self.db).notify_result(user, course, passed, score)
        self.db.commit()
        return attempt

    def can_retry(self, course_id: int, user: User) -> tuple[bool, int, int]:
        enrollment, course = self._enrollment(course_id, user)
        max_attempts = self._max_attempts(course)
        retry = (
            enrollment.status != EnrollmentStatus.COMPLETED
            and enrollment.attempts_used < max_attempts
        )
        return retry, enrollment.attempts_used, max_attempts
