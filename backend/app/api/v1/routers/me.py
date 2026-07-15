"""Employee self-service endpoints for assigned courses."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.models.question import QuizAttempt
from app.schemas.assignment import MyCourseOut
from app.schemas.course import CourseDetailOut
from app.schemas.quiz import (
    AnswerReview,
    QuizAttemptSummary,
    QuizQuestionView,
    QuizResult,
    QuizSubmitRequest,
    QuizView,
)
from app.services.assignment_service import AssignmentService
from app.services.course_service import CourseService
from app.services.quiz_service import QuizService
from app.utils import storage

router = APIRouter(prefix="/me/courses", tags=["My Courses"])


@router.get("", response_model=list[MyCourseOut])
def my_courses(db: DbSession, current_user: CurrentUser):
    return [MyCourseOut(**c) for c in AssignmentService(db).my_courses(current_user)]


@router.get("/{course_id}", response_model=CourseDetailOut)
def my_course_detail(course_id: int, db: DbSession, current_user: CurrentUser):
    _, course = AssignmentService(db).get_my_course(course_id, current_user)
    return CourseDetailOut.from_model(course)


@router.get("/{course_id}/documents/{document_id}/download")
def download_my_document(course_id: int, document_id: int, db: DbSession, current_user: CurrentUser):
    # Raises if the course is not assigned to this employee.
    AssignmentService(db).get_my_course(course_id, current_user)
    doc = CourseService(db).get_document(course_id, document_id)
    path = storage.resolve_path(doc.file_path)
    if not path or not path.is_file():
        raise NotFoundError("Document file is not available")
    return FileResponse(
        path, filename=doc.original_filename, media_type=doc.content_type or None
    )


# --------------------------------- Quiz ------------------------------------ #
def _build_view(db, attempt: QuizAttempt) -> QuizView:
    from app.models.course import Course

    course = db.get(Course, attempt.course_id)
    questions = sorted(attempt.answers, key=lambda a: a.display_order)
    return QuizView(
        attempt_id=attempt.id,
        course_id=attempt.course_id,
        course_name=course.name if course else "",
        status=attempt.status,
        total_questions=attempt.total_questions,
        passing_percentage=attempt.passing_percentage,
        attempt_number=attempt.attempt_number,
        started_at=attempt.started_at,
        questions=[
            QuizQuestionView(
                answer_id=a.id,
                question_id=a.question_id,
                question_type=a.question.question_type,
                difficulty=a.question.difficulty,
                question_text=a.question.question_text,
                options=a.presented_options,
                display_order=a.display_order,
            )
            for a in questions
        ],
    )


def _build_result(db, attempt: QuizAttempt, user) -> QuizResult:
    can_retry, used, max_attempts = QuizService(db).can_retry(attempt.course_id, user)
    review = [
        AnswerReview(
            question_text=a.question.question_text,
            options=a.presented_options,
            selected=a.selected_answer,
            correct_answer=a.correct_answer,
            is_correct=bool(a.is_correct),
            explanation=a.question.explanation,
            topic=a.question.topic,
        )
        for a in sorted(attempt.answers, key=lambda a: a.display_order)
    ]
    return QuizResult(
        attempt_id=attempt.id,
        course_id=attempt.course_id,
        total_questions=attempt.total_questions,
        correct_count=attempt.correct_count,
        score_percentage=float(attempt.score_percentage or 0),
        passing_percentage=attempt.passing_percentage,
        passed=bool(attempt.passed),
        status=attempt.status,
        submitted_at=attempt.submitted_at,
        can_retry=can_retry,
        attempts_used=used,
        max_attempts=max_attempts,
        review=review,
    )


@router.post("/{course_id}/quiz/start", response_model=QuizView)
def start_quiz(course_id: int, db: DbSession, current_user: CurrentUser):
    attempt = QuizService(db).start(course_id, current_user)
    return _build_view(db, QuizService(db).get_attempt(attempt.id, current_user))


@router.get("/{course_id}/quiz/attempts", response_model=list[QuizAttemptSummary])
def quiz_history(course_id: int, db: DbSession, current_user: CurrentUser):
    attempts = QuizService(db).history(course_id, current_user)
    return [
        QuizAttemptSummary(
            attempt_id=a.id,
            attempt_number=a.attempt_number,
            status=a.status,
            score_percentage=float(a.score_percentage) if a.score_percentage is not None else None,
            passed=a.passed,
            total_questions=a.total_questions,
            correct_count=a.correct_count,
            submitted_at=a.submitted_at,
        )
        for a in attempts
    ]


# Attempt-scoped endpoints (not nested under course for brevity)
quiz_router = APIRouter(prefix="/me/quiz", tags=["My Courses"])


@quiz_router.get("/{attempt_id}/view", response_model=QuizView)
def quiz_view(attempt_id: int, db: DbSession, current_user: CurrentUser):
    return _build_view(db, QuizService(db).get_attempt(attempt_id, current_user))


@quiz_router.post("/{attempt_id}/submit", response_model=QuizResult)
def submit_quiz(attempt_id: int, payload: QuizSubmitRequest, db: DbSession, current_user: CurrentUser):
    attempt = QuizService(db).submit(attempt_id, payload.answers, current_user)
    return _build_result(db, QuizService(db).get_attempt(attempt.id, current_user), current_user)


@quiz_router.get("/{attempt_id}/result", response_model=QuizResult)
def quiz_result(attempt_id: int, db: DbSession, current_user: CurrentUser):
    return _build_result(db, QuizService(db).get_attempt(attempt_id, current_user), current_user)


@router.post("/{course_id}/start", response_model=MyCourseOut)
def start_course(course_id: int, db: DbSession, current_user: CurrentUser):
    svc = AssignmentService(db)
    svc.start_course(course_id, current_user)
    return _single(svc, course_id, current_user)


@router.post("/{course_id}/complete-content", response_model=MyCourseOut)
def complete_content(course_id: int, db: DbSession, current_user: CurrentUser):
    svc = AssignmentService(db)
    svc.complete_content(course_id, current_user)
    return _single(svc, course_id, current_user)


def _single(svc: AssignmentService, course_id: int, user) -> MyCourseOut:
    for c in svc.my_courses(user):
        if c["course_id"] == course_id:
            return MyCourseOut(**c)
    # Fallback (should not happen): re-raise not found via detail fetch
    svc.get_my_course(course_id, user)
    raise RuntimeError("course state unavailable")
