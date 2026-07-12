"""Course & course-document schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import CourseStatus, CourseType, DocumentStatus


class CourseBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=120)
    trainer: Optional[str] = Field(None, max_length=160)
    course_type: CourseType = CourseType.OPTIONAL
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    has_quiz: bool = True
    passing_percentage: int = Field(50, ge=0, le=100)
    quiz_question_count: int = Field(10, ge=1, le=100)
    allow_retry: bool = True
    retry_count: int = Field(1, ge=0, le=20)

    @model_validator(mode="after")
    def _check_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class CourseCreate(CourseBase):
    pass


class AICourseGenerateRequest(BaseModel):
    """Create a course whose material is authored by AI from a topic brief.

    Carries the same course-configuration fields as ``CourseCreate`` (category,
    dates, retry policy, …); the name and description are authored by AI from the
    topic, and ``category`` is optional (AI suggests one when left blank).
    """

    topic: str = Field(..., min_length=3, max_length=300)
    extra_instructions: Optional[str] = Field(None, max_length=1000)
    # Standard course knobs, applied to the created course (mirrors CourseCreate).
    category: Optional[str] = Field(None, max_length=120)
    trainer: Optional[str] = Field(None, max_length=160)
    course_type: CourseType = CourseType.OPTIONAL
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    has_quiz: bool = True
    passing_percentage: int = Field(50, ge=0, le=100)
    quiz_question_count: int = Field(10, ge=1, le=100)
    allow_retry: bool = True
    retry_count: int = Field(1, ge=0, le=20)

    @model_validator(mode="after")
    def _check_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class TrendingCourseOut(BaseModel):
    """A single AI-suggested trending course the admin might add to the org."""

    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    level: str
    why: Optional[str] = None
    skills: list[str] = Field(default_factory=list)


class TrendingRecommendationsOut(BaseModel):
    items: list[TrendingCourseOut]
    focus: Optional[str] = None
    # "ai" when authored by Claude, "fallback" for the curated offline list.
    source: str


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=120)
    trainer: Optional[str] = Field(None, max_length=160)
    course_type: Optional[CourseType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    has_quiz: Optional[bool] = None
    passing_percentage: Optional[int] = Field(None, ge=0, le=100)
    quiz_question_count: Optional[int] = Field(None, ge=1, le=100)
    allow_retry: Optional[bool] = None
    retry_count: Optional[int] = Field(None, ge=0, le=20)


class LinkRequest(BaseModel):
    """Add course material from a URL (web page or direct file link)."""
    url: str = Field(..., min_length=4, max_length=2000)


class CourseDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_filename: str
    file_type: str
    content_type: Optional[str]
    size_bytes: int
    status: DocumentStatus
    processing_error: Optional[str] = None
    text_chars: int = 0
    source_url: Optional[str] = None
    created_at: datetime

    @classmethod
    def from_model(cls, doc) -> "CourseDocumentOut":
        return cls(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            content_type=doc.content_type,
            size_bytes=doc.size_bytes,
            status=doc.status,
            processing_error=doc.processing_error,
            text_chars=len(doc.extracted_text or ""),
            source_url=doc.source_url,
            created_at=doc.created_at,
        )


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    trainer: Optional[str] = None
    course_type: CourseType
    status: CourseStatus
    start_date: Optional[date]
    end_date: Optional[date]
    has_quiz: bool = True
    passing_percentage: int
    quiz_question_count: int
    allow_retry: bool
    retry_count: int
    thumbnail_path: Optional[str]
    document_count: int = 0
    # True once the due date (end_date) has passed — derived, not stored.
    is_expired: bool = False
    published_at: Optional[datetime] = None
    created_at: datetime


class CourseDetailOut(CourseOut):
    documents: list[CourseDocumentOut] = Field(default_factory=list)

    @classmethod
    def from_model(cls, course) -> "CourseDetailOut":
        base = CourseOut.model_validate(course).model_dump()
        base["documents"] = [CourseDocumentOut.from_model(d) for d in course.documents]
        return cls(**base)
