"""Generate and manage a course's AI question bank (Phase 5).

Generation runs in a background thread so the HTTP request returns immediately;
clients poll ``get_status`` for progress. A synchronous ``generate`` is kept for
tests and scripted use.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai import quiz_generator
from app.core.database import SessionLocal
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging_config import get_logger
from app.models.question import QuestionBank
from app.repositories.question_repository import QuestionBankRepository
from app.services.audit_service import AuditService
from app.services.course_service import CourseService

logger = get_logger(__name__)

# In-process generation job registry (single-worker dev/demo). Keyed by course id.
_JOBS: dict[int, dict] = {}
_LOCK = threading.Lock()


def _set_job(course_id: int, **fields) -> None:
    with _LOCK:
        job = _JOBS.setdefault(course_id, {})
        job.update(fields)


def get_status(course_id: int) -> dict:
    with _LOCK:
        job = _JOBS.get(course_id)
        return dict(job) if job else {"status": "idle"}


class QuizGenerationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QuestionBankRepository(db)
        self.courses = CourseService(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ #
    # Core (synchronous) generation used by the background worker & tests
    # ------------------------------------------------------------------ #
    def _generate_core(self, course_id: int, count: int, replace_existing: bool,
                       actor_id: int | None) -> dict:
        course = self.courses.get(course_id)  # raises if missing
        material = self.courses.extractable_text(course_id)
        if not material:
            raise BusinessRuleError(
                "No extractable text found. Upload and process a document first."
            )

        if replace_existing:
            removed = self.repo.clear_course(course_id)
            logger.info("Cleared %s existing questions for course %s", removed, course_id)
            self.db.flush()

        # Scope generation to the course subject so questions stay relevant even
        # when the uploaded material contains off-topic passages.
        subject = course.name
        if course.description:
            subject = f"{course.name} — {course.description}"
        questions, source = quiz_generator.generate_questions(material, count, subject)
        if not questions:
            raise BusinessRuleError("Could not generate questions from the available material.")

        existing = self.repo.existing_texts(course_id)
        added = 0
        for q in questions:
            key = q["question_text"].strip().lower()
            if key in existing:
                continue
            existing.add(key)
            self.repo.add(QuestionBank(
                course_id=course_id,
                question_type=q["question_type"],
                difficulty=q["difficulty"],
                question_text=q["question_text"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q.get("explanation"),
                topic=q.get("topic"),
                reference_section=q.get("reference_section"),
                generated_by=source,
            ))
            added += 1

        self.audit.record(action="course.questions.generate", user_id=actor_id,
                          entity_type="course", entity_id=course_id,
                          detail=f"source={source} added={added}")
        self.db.commit()
        return {
            "generated": added,
            "total_in_bank": self.repo.count(course_id),
            "source": source,
            "difficulty_breakdown": self.repo.group_counts(course_id, QuestionBank.difficulty),
            "type_breakdown": self.repo.group_counts(course_id, QuestionBank.question_type),
            "message": f"Generated {added} question(s) using the {source} generator.",
        }

    def generate(self, course_id: int, count: int, replace_existing: bool, actor) -> dict:
        """Synchronous generation (used by tests / scripts)."""
        return self._generate_core(course_id, count, replace_existing,
                                   actor.id if actor else None)

    # ------------------------------------------------------------------ #
    # Background generation
    # ------------------------------------------------------------------ #
    def start_async(self, course_id: int, count: int, replace_existing: bool, actor) -> dict:
        # Validate synchronously so obvious errors return immediately.
        course = self.courses.get(course_id)
        if course and not course.has_quiz:
            raise BusinessRuleError("This course is configured without a quiz.")
        if not self.courses.extractable_text(course_id):
            raise BusinessRuleError(
                "No extractable text found. Upload and process a document first."
            )
        with _LOCK:
            running = _JOBS.get(course_id, {}).get("status") == "running"
        if running:
            return {"status": "running", "message": "Generation already in progress."}

        _set_job(course_id, status="running", generated=0, source=None,
                 message="Generating questions…",
                 started_at=datetime.now(timezone.utc).isoformat())

        actor_id = actor.id if actor else None
        thread = threading.Thread(
            target=self._run_job,
            args=(course_id, count, replace_existing, actor_id),
            daemon=True,
        )
        thread.start()
        return {"status": "running", "message": "Generation started."}

    @staticmethod
    def _run_job(course_id: int, count: int, replace_existing: bool, actor_id: int | None) -> None:
        db = SessionLocal()
        try:
            result = QuizGenerationService(db)._generate_core(
                course_id, count, replace_existing, actor_id
            )
            _set_job(course_id, status="done", **result)
            logger.info("Generation job for course %s finished: %s", course_id, result["message"])
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.exception("Generation job for course %s failed", course_id)
            _set_job(course_id, status="error", message=str(exc))
        finally:
            db.close()

    # ------------------------------------------------------------------ #
    def list_questions(self, course_id: int, **kwargs) -> tuple[list[QuestionBank], int]:
        self.courses.get(course_id)
        rows, total = self.repo.for_course(course_id, **kwargs)
        return list(rows), total

    def stats(self, course_id: int) -> dict:
        self.courses.get(course_id)
        return {
            "total": self.repo.count(course_id),
            "difficulty_breakdown": self.repo.group_counts(course_id, QuestionBank.difficulty),
            "type_breakdown": self.repo.group_counts(course_id, QuestionBank.question_type),
            "generated_by": self.repo.group_counts(course_id, QuestionBank.generated_by),
        }

    def delete_question(self, course_id: int, question_id: int, actor) -> None:
        q = self.repo.get(question_id)
        if not q or q.course_id != course_id:
            raise NotFoundError("Question not found")
        self.repo.delete(q)
        self.db.commit()

    def clear(self, course_id: int, actor) -> int:
        self.courses.get(course_id)
        removed = self.repo.clear_course(course_id)
        self.audit.record(action="course.questions.clear", user_id=actor.id,
                          entity_type="course", entity_id=course_id, detail=str(removed))
        self.db.commit()
        return removed
