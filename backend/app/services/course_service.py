"""Course management business logic."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.ai import document_processor
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging_config import get_logger
from app.models.course import Course, CourseDocument
from app.models.enums import CourseStatus, CourseType, DocumentStatus
from app.models.user import User
from app.repositories.course_repository import (
    CourseDocumentRepository,
    CourseRepository,
)
from app.schemas.course import CourseCreate, CourseUpdate
from app.services.audit_service import AuditService
from app.utils import storage

logger = get_logger(__name__)


def _transcribe_in_background(document_id: int) -> None:
    """Transcribe an audio/video document in a daemon thread with its own DB
    session, so the upload request returns immediately."""

    def _work() -> None:
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            doc = db.get(CourseDocument, document_id)
            if doc is None:
                return
            CourseService(db)._run_extraction(doc)
            db.commit()
            logger.info("Background transcription for document %s -> %s",
                        document_id, doc.status.value)
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception("Background transcription failed for document %s", document_id)
        finally:
            db.close()

    threading.Thread(target=_work, name=f"transcribe-doc-{document_id}",
                     daemon=True).start()


class CourseService:
    def __init__(self, db: Session):
        self.db = db
        self.courses = CourseRepository(db)
        self.documents = CourseDocumentRepository(db)
        self.audit = AuditService(db)

    # ------------------------------ Read ------------------------------ #
    def get(self, course_id: int) -> Course:
        course = self.courses.get_with_documents(course_id)
        if not course:
            raise NotFoundError("Course not found")
        return course

    def list(self, **kwargs) -> tuple[list[Course], int]:
        rows, total = self.courses.search(**kwargs)
        return list(rows), total

    def categories(self) -> list[str]:
        return self.courses.categories()

    # ----------------------------- Create ----------------------------- #
    def create(self, data: CourseCreate, actor: User) -> Course:
        course = Course(
            **data.model_dump(),
            status=CourseStatus.DRAFT,
            created_by_id=actor.id,
        )
        self.courses.add(course)
        self.audit.record(action="course.create", user_id=actor.id,
                          entity_type="course", entity_id=course.id, detail=course.name)
        self.db.commit()
        return self.get(course.id)

    def generate_ai_course(self, data, actor: User) -> Course:
        """Create a DRAFT course whose training material is authored by AI.

        The generated text is stored as an ordinary (processed) course document,
        so the existing quiz-generation, publishing and viewer flows apply to it
        unchanged. The admin reviews it, generates questions, then publishes —
        exactly as with an uploaded document.
        """
        from app.ai import course_generator

        meta, content, source = course_generator.generate_course(
            topic=data.topic,
            extra=data.extra_instructions,
        )

        course = Course(
            name=meta["name"],
            description=meta["description"],
            # Admin-provided category wins; otherwise use the AI's suggestion.
            category=data.category or meta["category"],
            trainer=data.trainer,
            has_quiz=data.has_quiz,
            course_type=data.course_type,
            start_date=data.start_date,
            end_date=data.end_date,
            passing_percentage=data.passing_percentage,
            quiz_question_count=data.quiz_question_count,
            allow_retry=data.allow_retry,
            retry_count=data.retry_count,
            status=CourseStatus.DRAFT,
            created_by_id=actor.id,
        )
        self.courses.add(course)
        self.db.flush()  # need course.id for the document path

        file_meta = storage.save_text_document(
            content, subdir=f"courses/{course.id}", filename=f"{meta['name']} (AI generated)"
        )
        doc = CourseDocument(
            course_id=course.id,
            uploaded_by_id=actor.id,
            status=DocumentStatus.PROCESSED,
            extracted_text=content,
            **file_meta,
        )
        self.documents.add(doc)
        self.audit.record(action="course.ai_generate", user_id=actor.id,
                          entity_type="course", entity_id=course.id,
                          detail=f"source={source} topic={data.topic[:120]}")
        self.db.commit()
        return self.get(course.id)

    def update(self, course_id: int, data: CourseUpdate, actor: User) -> Course:
        course = self.get(course_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(course, field, value)
        # Re-validate date ordering after partial update
        if course.start_date and course.end_date and course.end_date < course.start_date:
            raise BusinessRuleError("end_date cannot be before start_date")
        self.audit.record(action="course.update", user_id=actor.id,
                          entity_type="course", entity_id=course.id)
        self.db.commit()
        # If the course is now mandatory & published, ensure all employees are enrolled.
        if course.course_type == CourseType.MANDATORY and course.status == CourseStatus.PUBLISHED:
            from app.services.assignment_service import AssignmentService
            AssignmentService(self.db).assign_all_active_employees(course, actor)
        return self.get(course.id)

    def delete(self, course_id: int, actor: User) -> None:
        course = self.get(course_id)
        for doc in course.documents:
            storage.delete_file(doc.file_path)
        storage.delete_file(course.thumbnail_path)
        self.courses.delete(course)
        self.audit.record(action="course.delete", user_id=actor.id,
                          entity_type="course", entity_id=course_id)
        self.db.commit()

    # --------------------------- Publishing --------------------------- #
    def publish(self, course_id: int, actor: User) -> Course:
        course = self.get(course_id)
        if not course.documents:
            raise BusinessRuleError(
                "Add at least one training material before publishing"
            )
        course.status = CourseStatus.PUBLISHED
        course.published_at = datetime.now(timezone.utc)
        self.audit.record(action="course.publish", user_id=actor.id,
                          entity_type="course", entity_id=course.id)
        self.db.flush()
        from app.services.notification_service import NotificationService
        NotificationService(self.db).notify_published(course)
        self.db.commit()
        # Mandatory courses are automatically assigned to all active employees.
        if course.course_type == CourseType.MANDATORY:
            from app.services.assignment_service import AssignmentService
            AssignmentService(self.db).assign_all_active_employees(course, actor)
        return self.get(course.id)

    def unpublish(self, course_id: int, actor: User) -> Course:
        course = self.get(course_id)
        course.status = CourseStatus.DRAFT
        self.audit.record(action="course.unpublish", user_id=actor.id,
                          entity_type="course", entity_id=course.id)
        self.db.commit()
        return self.get(course.id)

    # ---------------------------- Documents --------------------------- #
    def add_document(self, course_id: int, upload: UploadFile, actor: User) -> CourseDocument:
        course = self.get(course_id)
        meta = storage.save_upload(upload, subdir=f"courses/{course.id}")
        doc = CourseDocument(course_id=course.id, uploaded_by_id=actor.id, **meta)
        self.documents.add(doc)
        self.audit.record(action="course.document.upload", user_id=actor.id,
                          entity_type="course_document", entity_id=doc.id,
                          detail=meta["original_filename"])
        self.db.flush()
        if document_processor.is_media(doc.original_filename):
            # Audio/video transcription is slow (speech-to-text). Mark the file
            # as processing, return the upload immediately, and transcribe in a
            # background thread so the request doesn't hang on long media.
            doc.status = DocumentStatus.PROCESSING
            doc.extracted_text = None
            doc.processing_error = None
            self.db.commit()
            _transcribe_in_background(doc.id)
        else:
            # Documents extract quickly — do it inline.
            self._run_extraction(doc)
            self.db.commit()
        return doc

    def add_link(self, course_id: int, url: str, actor: User) -> CourseDocument:
        """Add course material from a URL — a web page (text extracted) or a
        direct file link (downloaded, then extracted/transcribed like an upload)."""
        from app.ai import url_ingest

        course = self.get(course_id)
        res = url_ingest.fetch(url)

        if res["kind"] == "html":
            meta = storage.save_text_document(
                res["text"], subdir=f"courses/{course.id}",
                filename=(res["title"][:80] or "web-page"),
            )
            doc = CourseDocument(course_id=course.id, uploaded_by_id=actor.id, **meta)
            # Show the page title / source link rather than the stored .txt name.
            # The text is already extracted, so set it directly (no re-parsing).
            doc.original_filename = (res["title"] or res["url"])[:250]
            doc.source_url = res["url"]
            doc.extracted_text = res["text"]
            doc.status = DocumentStatus.PROCESSED
            doc.processing_error = None
            self.documents.add(doc)
            self.db.flush()
            self.db.commit()
        else:
            meta = storage.save_bytes(
                res["data"], subdir=f"courses/{course.id}",
                filename=res["filename"], content_type=res.get("content_type"),
            )
            doc = CourseDocument(course_id=course.id, uploaded_by_id=actor.id, **meta)
            doc.source_url = res["url"]
            self.documents.add(doc)
            self.db.flush()
            if document_processor.is_media(doc.original_filename):
                doc.status = DocumentStatus.PROCESSING
                doc.extracted_text = None
                doc.processing_error = None
                self.db.commit()
                _transcribe_in_background(doc.id)
            else:
                self._run_extraction(doc)
                self.db.commit()

        self.audit.record(action="course.document.link", user_id=actor.id,
                          entity_type="course_document", entity_id=doc.id,
                          detail=res["url"][:255])
        self.db.commit()
        return doc

    def _run_extraction(self, doc: CourseDocument) -> None:
        if not document_processor.can_extract(doc.original_filename):
            # Non-text media: nothing to extract, but not an error.
            doc.status = DocumentStatus.PROCESSED
            doc.extracted_text = None
            doc.processing_error = None
            return
        try:
            doc.status = DocumentStatus.PROCESSING
            text = document_processor.extract_text(str(storage.resolve_path(doc.file_path)))
            doc.extracted_text = text
            doc.status = DocumentStatus.PROCESSED
            doc.processing_error = None
        except Exception as exc:  # noqa: BLE001 - record and continue
            logger.warning("Document %s extraction failed: %s", doc.id, exc)
            doc.status = DocumentStatus.FAILED
            doc.processing_error = str(exc)[:2000]

    def process_document(self, course_id: int, document_id: int, actor: User) -> CourseDocument:
        doc = self.get_document(course_id, document_id)
        self._run_extraction(doc)
        self.audit.record(action="course.document.process", user_id=actor.id,
                          entity_type="course_document", entity_id=doc.id,
                          detail=doc.status.value)
        self.db.commit()
        return doc

    def process_all_documents(self, course_id: int, actor: User) -> list[CourseDocument]:
        course = self.get(course_id)
        for doc in course.documents:
            self._run_extraction(doc)
        self.db.commit()
        return list(course.documents)

    def extractable_text(self, course_id: int) -> str:
        """Concatenated cleaned text of all processed documents for a course."""
        course = self.get(course_id)
        chunks = [d.extracted_text for d in course.documents if d.extracted_text]
        return "\n\n".join(chunks)

    def set_thumbnail(self, course_id: int, upload: UploadFile, actor: User) -> Course:
        course = self.get(course_id)
        storage.delete_file(course.thumbnail_path)
        meta = storage.save_upload(upload, subdir=f"courses/{course.id}/thumbnail")
        course.thumbnail_path = meta["file_path"]
        self.db.commit()
        return self.get(course.id)

    def delete_document(self, course_id: int, document_id: int, actor: User) -> None:
        doc = self.documents.get(document_id)
        if not doc or doc.course_id != course_id:
            raise NotFoundError("Document not found")
        storage.delete_file(doc.file_path)
        self.documents.delete(doc)
        self.audit.record(action="course.document.delete", user_id=actor.id,
                          entity_type="course_document", entity_id=document_id)
        self.db.commit()

    def get_document(self, course_id: int, document_id: int) -> CourseDocument:
        doc = self.documents.get(document_id)
        if not doc or doc.course_id != course_id:
            raise NotFoundError("Document not found")
        return doc
