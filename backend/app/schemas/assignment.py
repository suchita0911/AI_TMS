"""Course assignment & enrollment schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    AssignmentTargetType,
    CourseType,
    EnrollmentStatus,
)


class AssignRequest(BaseModel):
    target_type: AssignmentTargetType
    department_id: Optional[int] = None
    group_id: Optional[int] = None
    user_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_target(self):
        if self.target_type == AssignmentTargetType.DEPARTMENT and not self.department_id:
            raise ValueError("department_id is required for a department assignment")
        if self.target_type == AssignmentTargetType.GROUP and not self.group_id:
            raise ValueError("group_id is required for a group assignment")
        if self.target_type in (
            AssignmentTargetType.INDIVIDUAL,
        ) and not self.user_ids:
            raise ValueError("user_ids is required for an individual assignment")
        return self


class AssignResult(BaseModel):
    assigned: int
    already_assigned: int
    total_targeted: int
    message: str


class EnrolledUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    username: str
    email: str
    department: Optional[str] = None


class EnrollmentOut(BaseModel):
    """Admin-facing enrollment row for a course."""

    id: int
    status: EnrollmentStatus
    best_score: Optional[float] = None
    attempts_used: int
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    user: EnrolledUser


class MyCourseOut(BaseModel):
    """Employee-facing view of an assigned course + their progress."""

    course_id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    course_type: CourseType
    start_date: Optional[date]
    end_date: Optional[date]
    has_quiz: bool = True
    passing_percentage: int
    quiz_question_count: int
    document_count: int
    status: EnrollmentStatus
    best_score: Optional[float] = None
    attempts_used: int = 0
    max_attempts: int = 1
    can_attempt_quiz: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_overdue: bool = False
