"""Question bank schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DifficultyLevel, QuestionType


class QuestionGenerateRequest(BaseModel):
    count: int = Field(100, ge=1, le=300)
    replace_existing: bool = False


class QuestionBankOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_id: int
    question_type: QuestionType
    difficulty: DifficultyLevel
    question_text: str
    options: list[str]
    correct_answer: str
    explanation: Optional[str]
    topic: Optional[str]
    reference_section: Optional[str]
    generated_by: str
    is_active: bool
    created_at: datetime


class GenerationResult(BaseModel):
    generated: int
    total_in_bank: int
    source: str  # ai | fallback | none
    difficulty_breakdown: dict[str, int]
    type_breakdown: dict[str, int]
    message: str


class GenerationStart(BaseModel):
    status: str  # running
    message: str


class GenerationStatus(BaseModel):
    status: str  # idle | running | done | error
    generated: Optional[int] = None
    total_in_bank: Optional[int] = None
    source: Optional[str] = None
    message: Optional[str] = None
    difficulty_breakdown: Optional[dict[str, int]] = None
    type_breakdown: Optional[dict[str, int]] = None


class QuestionBankStats(BaseModel):
    total: int
    difficulty_breakdown: dict[str, int]
    type_breakdown: dict[str, int]
    generated_by: dict[str, int]
