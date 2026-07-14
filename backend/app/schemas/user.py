"""User / Department / Group schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RoleName, UserStatus
from app.schemas.common import Email, EmployeeId, RequiredEmployeeId, USERNAME_PATTERN


# --------------------------------------------------------------------------- #
# Department
# --------------------------------------------------------------------------- #
class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=255)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class DepartmentOut(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


# --------------------------------------------------------------------------- #
# Designation (job-title catalogue)
# --------------------------------------------------------------------------- #
class DesignationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)


class DesignationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# --------------------------------------------------------------------------- #
# Group
# --------------------------------------------------------------------------- #
class GroupBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=255)


class GroupCreate(GroupBase):
    member_ids: list[int] = Field(default_factory=list)


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    member_ids: Optional[list[int]] = None


class GroupOut(GroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    member_count: int = 0
    created_at: datetime


# --------------------------------------------------------------------------- #
# User
# --------------------------------------------------------------------------- #
class UserBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    # Optional: the UI logs in by email, so if no username is supplied one is
    # derived from the email address server-side.
    username: Optional[str] = Field(None, min_length=3, max_length=80, pattern=USERNAME_PATTERN)
    email: Email
    department_id: Optional[int] = None
    employee_id: RequiredEmployeeId = Field(..., max_length=50)
    # Job title / seniority; feeds AI course recommendations.
    designation: Optional[str] = Field(None, max_length=120)


class UserCreate(UserBase):
    """Admin-driven creation. Password is optional (temporary)."""

    role: RoleName = RoleName.EMPLOYEE
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=80)
    last_name: Optional[str] = Field(None, min_length=1, max_length=80)
    email: Optional[Email] = None
    department_id: Optional[int] = None
    employee_id: EmployeeId = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=120)
    role: Optional[RoleName] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class DepartmentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    username: str
    email: Email
    employee_id: Optional[str]
    designation: Optional[str] = None
    status: UserStatus
    is_active: bool
    role: RoleName
    department: Optional[DepartmentBrief] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    @classmethod
    def from_model(cls, user):
        return cls(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            email=user.email,
            employee_id=user.employee_id,
            designation=user.designation,
            status=user.status,
            is_active=user.is_active,
            role=user.role.name,
            department=user.department,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )


class UserCreateResponse(UserOut):
    """UserOut plus the one-time password-setup token, returned when an admin
    creates an employee without a password (so the link can be shared)."""

    setup_token: Optional[str] = None
