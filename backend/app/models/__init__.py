"""Import all models so that ``Base.metadata`` is fully populated.

New phases add their models here as they are introduced.
"""
from app.models.auth import AuditLog, PasswordToken
from app.models.certificate import Certificate
from app.models.course import (
    Course,
    CourseAssignment,
    CourseDocument,
    EmployeeCourseStatus,
)
from app.models.notification import Notification
from app.models.question import QuestionBank, QuizAnswer, QuizAttempt
from app.models.user import (
    Department,
    Group,
    Role,
    User,
    group_members,
)

__all__ = [
    "AuditLog",
    "PasswordToken",
    "Course",
    "CourseAssignment",
    "CourseDocument",
    "EmployeeCourseStatus",
    "QuestionBank",
    "QuizAttempt",
    "QuizAnswer",
    "Notification",
    "Certificate",
    "Department",
    "Group",
    "Role",
    "User",
    "group_members",
]
