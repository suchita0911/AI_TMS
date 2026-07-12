"""Quiz-taking schemas (employee-facing)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.enums import DifficultyLevel, QuestionType, QuizAttemptStatus


class QuizQuestionView(BaseModel):
    """A question as presented to the employee — no correct answer exposed."""

    answer_id: int
    question_id: int
    question_type: QuestionType
    difficulty: DifficultyLevel
    question_text: str
    options: list[str]
    display_order: int


class QuizView(BaseModel):
    attempt_id: int
    course_id: int
    course_name: str
    status: QuizAttemptStatus
    total_questions: int
    passing_percentage: int
    attempt_number: int
    started_at: datetime
    questions: list[QuizQuestionView]


class SubmittedAnswer(BaseModel):
    answer_id: int
    selected: Optional[str] = None


class QuizSubmitRequest(BaseModel):
    answers: list[SubmittedAnswer]


class AnswerReview(BaseModel):
    question_text: str
    options: list[str]
    selected: Optional[str]
    correct_answer: str
    is_correct: bool
    explanation: Optional[str]
    topic: Optional[str] = None


class QuizResult(BaseModel):
    attempt_id: int
    course_id: int
    total_questions: int
    correct_count: int
    score_percentage: float
    passing_percentage: int
    passed: bool
    status: QuizAttemptStatus
    submitted_at: Optional[datetime]
    can_retry: bool
    attempts_used: int
    max_attempts: int
    review: list[AnswerReview] = []


class QuizAttemptSummary(BaseModel):
    attempt_id: int
    attempt_number: int
    status: QuizAttemptStatus
    score_percentage: Optional[float]
    passed: Optional[bool]
    total_questions: int
    correct_count: int
    submitted_at: Optional[datetime]
