"""Course, course document and enrollment (employee course status) models."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import (
    AssignmentTargetType,
    CourseStatus,
    CourseType,
    DocumentStatus,
    EnrollmentStatus,
)
from app.models.types import EnumType


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    # Optional instructor/trainer name for the course.
    trainer: Mapped[Optional[str]] = mapped_column(String(160))
    course_type: Mapped[CourseType] = mapped_column(
        EnumType(CourseType), default=CourseType.OPTIONAL, nullable=False
    )
    status: Mapped[CourseStatus] = mapped_column(
        EnumType(CourseStatus), default=CourseStatus.DRAFT, nullable=False, index=True
    )

    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)

    # Whether this course includes a quiz. When False, completing the content
    # completes the course directly (no assessment).
    has_quiz: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    passing_percentage: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    quiz_question_count: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    allow_retry: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500))

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    documents: Mapped[list["CourseDocument"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )

    @property
    def document_count(self) -> int:
        return len(self.documents)

    @property
    def is_expired(self) -> bool:
        """True once the course due date (``end_date``) is in the past."""
        return bool(self.end_date and self.end_date < date.today())


class CourseDocument(Base, TimestampMixin):
    __tablename__ = "course_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(120))
    file_type: Mapped[str] = mapped_column(String(20))  # pdf, docx, mp4, ...
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Set when the material was added from a URL; the original link to open.
    source_url: Mapped[Optional[str]] = mapped_column(String(2000))

    # Populated in Phase 4 (AI document processing)
    status: Mapped[DocumentStatus] = mapped_column(
        EnumType(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    processing_error: Mapped[Optional[str]] = mapped_column(Text)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    course: Mapped["Course"] = relationship(back_populates="documents")


class CourseAssignment(Base, TimestampMixin):
    """Record of an assignment action (audit/history of who a course targeted)."""

    __tablename__ = "course_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_type: Mapped[AssignmentTargetType] = mapped_column(
        EnumType(AssignmentTargetType), nullable=False
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL")
    )
    # For an "individual" assignment, the specific target user.
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assigned_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    course: Mapped["Course"] = relationship()


class EmployeeCourseStatus(Base, TimestampMixin):
    """Per-employee enrollment & progress record for a course."""

    __tablename__ = "employee_course_status"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_enrollment_course_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        EnumType(EnrollmentStatus), default=EnrollmentStatus.NOT_STARTED, nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    content_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    best_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    attempts_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    course: Mapped["Course"] = relationship()
    user: Mapped["object"] = relationship("User")
