"""Course management endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession, require_admin
from app.core.exceptions import NotFoundError
from app.utils import storage
from app.models.enums import CourseStatus, CourseType
from app.schemas.assignment import (
    AssignRequest,
    AssignResult,
    EnrolledUser,
    EnrollmentOut,
)
from app.schemas.common import Message, Page
from app.models.enums import DifficultyLevel, QuestionType
from app.schemas.course import (
    AICourseGenerateRequest,
    CourseCreate,
    CourseDetailOut,
    CourseDocumentOut,
    LinkRequest,
    CourseOut,
    CourseUpdate,
    TrendingCourseOut,
    TrendingRecommendationsOut,
)
from app.schemas.question import (
    GenerationStart,
    GenerationStatus,
    QuestionBankOut,
    QuestionBankStats,
    QuestionGenerateRequest,
)
from app.ai import trending_recommender
from app.services.assignment_service import AssignmentService
from app.services.course_service import CourseService
from app.services import quiz_generation_service
from app.services.quiz_generation_service import QuizGenerationService


def _enrollment_out(e) -> EnrollmentOut:
    return EnrollmentOut(
        id=e.id,
        status=e.status,
        best_score=float(e.best_score) if e.best_score is not None else None,
        attempts_used=e.attempts_used,
        assigned_at=e.assigned_at,
        started_at=e.started_at,
        completed_at=e.completed_at,
        user=EnrolledUser(
            id=e.user.id,
            first_name=e.user.first_name,
            last_name=e.user.last_name,
            username=e.user.username,
            email=e.user.email,
            department=e.user.department.name if e.user.department else None,
        ),
    )

# All /courses endpoints are admin-facing. Employees access their assigned
# courses through /me/courses (see routers/me.py), which enforces enrollment.
router = APIRouter(prefix="/courses", tags=["Courses"], dependencies=[Depends(require_admin)])
admin_router = APIRouter(
    prefix="/courses", tags=["Courses"], dependencies=[Depends(require_admin)]
)


# ------------------------------ Reads (any authenticated user) ------------- #
@router.get("", response_model=Page[CourseOut])
def list_courses(
    db: DbSession,
    current_user: CurrentUser,
    q: Optional[str] = None,
    status_filter: Optional[CourseStatus] = Query(None, alias="status"),
    course_type: Optional[CourseType] = None,
    category: Optional[str] = None,
    expired: Optional[bool] = Query(None, description="True = only published courses past their due date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
):
    items, total = CourseService(db).list(
        query=q, status=status_filter, course_type=course_type, category=category,
        expired=expired,
        offset=(page - 1) * page_size, limit=page_size,
    )
    return Page[CourseOut](
        items=[CourseOut.model_validate(c) for c in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/categories", response_model=list[str])
def list_categories(db: DbSession, current_user: CurrentUser):
    return CourseService(db).categories()


@router.get("/trending", response_model=TrendingRecommendationsOut)
def trending_courses(
    db: DbSession,
    current_user: CurrentUser,
    focus: Optional[str] = Query(None, description="Optional focus area, e.g. 'Cloud' or 'Security'"),
    designation: Optional[str] = Query(None, description="Optional job designation to tailor recommendations for, e.g. 'Senior Software Engineer'"),
    level: Optional[str] = Query(None, description="Optional difficulty level: beginner, intermediate, or advanced"),
    count: int = Query(6, ge=1, le=12),
):
    """AI-recommended trending IT-industry courses the admin might roll out.

    Existing catalogue titles are excluded so suggestions stay fresh. An optional
    ``designation`` tailors the picks to a specific job role. Degrades to a
    curated list when no AI key is configured (``source: 'fallback'``).
    """
    existing, _ = CourseService(db).list(limit=100)
    items, source = trending_recommender.recommend(
        focus=focus or "",
        count=count,
        exclude=[c.name for c in existing],
        designation=designation or "",
        level=level or "",
    )
    return TrendingRecommendationsOut(
        items=[TrendingCourseOut(**i) for i in items],
        focus=focus or None,
        designation=designation or None,
        level=level or None,
        source=source,
    )


@router.get("/{course_id}", response_model=CourseDetailOut)
def get_course(course_id: int, db: DbSession, current_user: CurrentUser):
    return CourseDetailOut.from_model(CourseService(db).get(course_id))


@router.get("/{course_id}/documents/{document_id}/download")
def download_document(course_id: int, document_id: int, db: DbSession, current_user: CurrentUser):
    doc = CourseService(db).get_document(course_id, document_id)
    # Resolve the stored (portable) path to an absolute one and confirm the file
    # exists, so a missing file returns a clean 404 instead of letting
    # FileResponse raise at send time and surface as an opaque 500.
    path = storage.resolve_path(doc.file_path)
    if not path or not path.is_file():
        raise NotFoundError("Document file is not available")
    return FileResponse(
        path, filename=doc.original_filename, media_type=doc.content_type or None
    )


# ------------------------------ Admin writes ------------------------------- #
@admin_router.post("", response_model=CourseDetailOut, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: DbSession, current_user: CurrentUser):
    return CourseDetailOut.from_model(CourseService(db).create(payload, current_user))


@admin_router.post("/generate", response_model=CourseDetailOut,
                   status_code=status.HTTP_201_CREATED)
def generate_ai_course(payload: AICourseGenerateRequest, db: DbSession,
                       current_user: CurrentUser):
    """Author a new DRAFT course from a topic using AI (content only).

    The generated material is stored as a course document, so the admin can then
    generate questions, review and publish exactly as with an uploaded document.
    """
    return CourseDetailOut.from_model(
        CourseService(db).generate_ai_course(payload, current_user)
    )


@admin_router.patch("/{course_id}", response_model=CourseDetailOut)
def update_course(course_id: int, payload: CourseUpdate, db: DbSession, current_user: CurrentUser):
    return CourseDetailOut.from_model(CourseService(db).update(course_id, payload, current_user))


@admin_router.delete("/{course_id}", response_model=Message)
def delete_course(course_id: int, db: DbSession, current_user: CurrentUser):
    CourseService(db).delete(course_id, current_user)
    return Message(detail="Course deleted")


@admin_router.post("/{course_id}/publish", response_model=CourseDetailOut)
def publish_course(course_id: int, db: DbSession, current_user: CurrentUser):
    return CourseDetailOut.from_model(CourseService(db).publish(course_id, current_user))


@admin_router.post("/{course_id}/unpublish", response_model=CourseDetailOut)
def unpublish_course(course_id: int, db: DbSession, current_user: CurrentUser):
    return CourseDetailOut.from_model(CourseService(db).unpublish(course_id, current_user))


@admin_router.post("/{course_id}/documents", response_model=CourseDocumentOut,
                   status_code=status.HTTP_201_CREATED)
def upload_document(course_id: int, db: DbSession, current_user: CurrentUser,
                    file: UploadFile = File(...)):
    doc = CourseService(db).add_document(course_id, file, current_user)
    return CourseDocumentOut.from_model(doc)


@admin_router.post("/{course_id}/link", response_model=CourseDocumentOut,
                   status_code=status.HTTP_201_CREATED)
def add_link(course_id: int, payload: LinkRequest, db: DbSession, current_user: CurrentUser):
    """Add course material from a URL (web page or direct file link)."""
    doc = CourseService(db).add_link(course_id, payload.url, current_user)
    return CourseDocumentOut.from_model(doc)


@admin_router.post("/{course_id}/thumbnail", response_model=CourseDetailOut)
def upload_thumbnail(course_id: int, db: DbSession, current_user: CurrentUser,
                     file: UploadFile = File(...)):
    return CourseDetailOut.from_model(
        CourseService(db).set_thumbnail(course_id, file, current_user)
    )


@admin_router.delete("/{course_id}/documents/{document_id}", response_model=Message)
def delete_document(course_id: int, document_id: int, db: DbSession, current_user: CurrentUser):
    CourseService(db).delete_document(course_id, document_id, current_user)
    return Message(detail="Document deleted")


@admin_router.post("/{course_id}/documents/{document_id}/process",
                   response_model=CourseDocumentOut)
def process_document(course_id: int, document_id: int, db: DbSession, current_user: CurrentUser):
    doc = CourseService(db).process_document(course_id, document_id, current_user)
    return CourseDocumentOut.from_model(doc)


@admin_router.post("/{course_id}/process", response_model=CourseDetailOut)
def process_all_documents(course_id: int, db: DbSession, current_user: CurrentUser):
    CourseService(db).process_all_documents(course_id, current_user)
    return CourseDetailOut.from_model(CourseService(db).get(course_id))


# ------------------------------ Assignment --------------------------------- #
@admin_router.post("/{course_id}/assign", response_model=AssignResult)
def assign_course(course_id: int, payload: AssignRequest, db: DbSession, current_user: CurrentUser):
    return AssignResult(**AssignmentService(db).assign(course_id, payload, current_user))


@admin_router.get("/{course_id}/enrollments", response_model=list[EnrollmentOut])
def course_enrollments(course_id: int, db: DbSession, current_user: CurrentUser):
    return [_enrollment_out(e) for e in AssignmentService(db).list_enrollments(course_id)]


@admin_router.delete("/{course_id}/enrollments/{user_id}", response_model=Message)
def unassign_course(course_id: int, user_id: int, db: DbSession, current_user: CurrentUser):
    AssignmentService(db).unassign(course_id, user_id, current_user)
    return Message(detail="Employee unassigned")


# --------------------------- Question bank (AI) ---------------------------- #
@admin_router.post("/{course_id}/generate-questions", response_model=GenerationStart)
def generate_questions(course_id: int, payload: QuestionGenerateRequest,
                       db: DbSession, current_user: CurrentUser):
    # Runs in the background; poll /generation-status for progress.
    result = QuizGenerationService(db).start_async(
        course_id, payload.count, payload.replace_existing, current_user
    )
    return GenerationStart(**result)


@admin_router.get("/{course_id}/generation-status", response_model=GenerationStatus)
def generation_status(course_id: int, db: DbSession, current_user: CurrentUser):
    return GenerationStatus(**quiz_generation_service.get_status(course_id))


@admin_router.get("/{course_id}/questions", response_model=Page[QuestionBankOut])
def list_questions(
    course_id: int, db: DbSession, current_user: CurrentUser,
    difficulty: Optional[DifficultyLevel] = None,
    question_type: Optional[QuestionType] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = QuizGenerationService(db).list_questions(
        course_id, difficulty=difficulty, question_type=question_type,
        offset=(page - 1) * page_size, limit=page_size,
    )
    return Page[QuestionBankOut](
        items=[QuestionBankOut.model_validate(q) for q in items],
        total=total, page=page, page_size=page_size,
    )


@admin_router.get("/{course_id}/questions/stats", response_model=QuestionBankStats)
def question_stats(course_id: int, db: DbSession, current_user: CurrentUser):
    return QuestionBankStats(**QuizGenerationService(db).stats(course_id))


@admin_router.delete("/{course_id}/questions", response_model=Message)
def clear_questions(course_id: int, db: DbSession, current_user: CurrentUser):
    removed = QuizGenerationService(db).clear(course_id, current_user)
    return Message(detail=f"Removed {removed} questions")


@admin_router.delete("/{course_id}/questions/{question_id}", response_model=Message)
def delete_question(course_id: int, question_id: int, db: DbSession, current_user: CurrentUser):
    QuizGenerationService(db).delete_question(course_id, question_id, current_user)
    return Message(detail="Question deleted")
