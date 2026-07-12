"""Shared schema utilities."""
from __future__ import annotations

import re
from typing import Annotated, Generic, Optional, TypeVar

from pydantic import AfterValidator, BaseModel, Field

T = TypeVar("T")

# Allowed characters for a username. Permits a plain handle (``john.doe``) as
# well as an email address used as the username (``john@corp.local``) — the
# only hard rule is "no spaces / control chars".
USERNAME_PATTERN = r"^[A-Za-z0-9._%+@-]+$"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("value is not a valid email address")
    return value.lower()


# Email type that accepts internal/enterprise domains (e.g. ``user@corp.local``)
# which the strict RFC deliverability check in ``EmailStr`` rejects.
Email = Annotated[str, AfterValidator(_validate_email)]


def _normalize_employee_id(value: Optional[str]) -> Optional[str]:
    """Trim whitespace and treat a blank employee id as absent, so that many
    records without one don't collide under the uniqueness rule."""
    if value is None:
        return None
    value = value.strip()
    return value or None


# Optional employee id, normalized so that "" / whitespace becomes ``None``.
EmployeeId = Annotated[Optional[str], AfterValidator(_normalize_employee_id)]


def _require_employee_id(value: str) -> str:
    """Trim and require a non-blank employee id."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Employee ID is required")
    return value


# Mandatory employee id (used when creating/registering a user).
RequiredEmployeeId = Annotated[str, AfterValidator(_require_employee_id)]


class Message(BaseModel):
    detail: str


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0
