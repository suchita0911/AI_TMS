"""Enumerations shared across models and schemas."""
from __future__ import annotations

import enum


class RoleName(str, enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class UserStatus(str, enum.Enum):
    PENDING = "pending"          # registered, password not set yet
    ACTIVE = "active"
    INACTIVE = "inactive"


class CourseType(str, enum.Enum):
    MANDATORY = "mandatory"
    OPTIONAL = "optional"


class CourseStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AssignmentTargetType(str, enum.Enum):
    ALL = "all"
    DEPARTMENT = "department"
    GROUP = "group"
    INDIVIDUAL = "individual"


class EnrollmentStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    QUIZ_PENDING = "quiz_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    OVERDUE = "overdue"
    # Assigned but not completed by the course due date. Terminal: the employee
    # can no longer start, resume or take the quiz. Computed at read time.
    EXPIRED = "expired"


class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    SCENARIO = "scenario"


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class QuizAttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    PASSED = "passed"
    FAILED = "failed"
