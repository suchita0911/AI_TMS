"""User, Role, Department, Group and related association tables."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Column,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import RoleName, UserStatus
from app.models.types import EnumType

# Many-to-many: users <-> groups
group_members = Table(
    "group_members",
    Base.metadata,
    Column("group_id", ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[RoleName] = mapped_column(EnumType(RoleName), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    users: Mapped[list["User"]] = relationship(back_populates="role")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="department")


class Designation(Base, TimestampMixin):
    """Catalogue of job designations offered in the employee forms and the AI
    recommendation picker. Admins can add new ones on the fly; the value stored
    on ``User.designation`` is the plain name, so this table is just the
    convenience list of known options."""

    __tablename__ = "designations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Group(Base, TimestampMixin):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    members: Mapped[list["User"]] = relationship(
        secondary=group_members, back_populates="groups"
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
        # NULL employee ids are allowed to repeat (Postgres treats NULLs as
        # distinct); only real, non-blank ids must be unique.
        UniqueConstraint("employee_id", name="uq_users_employee_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    username: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    # Job title / seniority (e.g. "Senior Software Engineer"). Used, among other
    # things, to let the AI tailor course recommendations to the employee's role.
    designation: Mapped[Optional[str]] = mapped_column(String(120))

    hashed_password: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[UserStatus] = mapped_column(
        EnumType(UserStatus), default=UserStatus.PENDING, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )

    role: Mapped["Role"] = relationship(back_populates="users", lazy="joined")
    department: Mapped[Optional["Department"]] = relationship(
        back_populates="users", lazy="joined"
    )
    groups: Mapped[list["Group"]] = relationship(
        secondary=group_members, back_populates="members"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
