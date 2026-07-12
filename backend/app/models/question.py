"""Question bank, quiz, quiz attempts and answers."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import DifficultyLevel, QuestionType, QuizAttemptStatus
from app.models.types import EnumType


class QuestionBank(Base, TimestampMixin):
    """AI-generated question grounded in a course's training material."""

    __tablename__ = "question_bank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_type: Mapped[QuestionType] = mapped_column(
        EnumType(QuestionType), nullable=False
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        EnumType(DifficultyLevel), nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # List of option strings (2 for true/false, 4 for mcq/scenario)
    options: Mapped[list] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    topic: Mapped[Optional[str]] = mapped_column(String(200))
    reference_section: Mapped[Optional[str]] = mapped_column(String(300))

    source_document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_documents.id", ondelete="SET NULL")
    )
    generated_by: Mapped[str] = mapped_column(String(30), default="ai")  # ai | fallback
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class QuizAttempt(Base, TimestampMixin):
    """One quiz attempt by an employee for a course."""

    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[QuizAttemptStatus] = mapped_column(
        EnumType(QuizAttemptStatus), default=QuizAttemptStatus.IN_PROGRESS, nullable=False
    )
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    passing_percentage: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    answers: Mapped[list["QuizAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class QuizAnswer(Base, TimestampMixin):
    """A single question presented in an attempt + the employee's response."""

    __tablename__ = "quiz_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("question_bank.id", ondelete="CASCADE"), nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # The options as presented to the user (shuffled), stored for review.
    presented_options: Mapped[list] = mapped_column(JSON, nullable=False)
    selected_answer: Mapped[Optional[str]] = mapped_column(Text)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)

    attempt: Mapped["QuizAttempt"] = relationship(back_populates="answers")
    question: Mapped["QuestionBank"] = relationship()
