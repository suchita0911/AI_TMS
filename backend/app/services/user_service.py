"""User, department and group management (admin operations)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.security import create_password_setup_token, decode_token, hash_password
from app.models.auth import PasswordToken
from app.models.enums import UserStatus
from app.models.user import Department, Group, User
from app.repositories.user_repository import (
    DepartmentRepository,
    GroupRepository,
    RoleRepository,
    UserRepository,
)
from app.schemas.user import (
    DepartmentCreate,
    DepartmentUpdate,
    GroupCreate,
    GroupUpdate,
    UserCreate,
    UserUpdate,
)
from app.utils import email


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.departments = DepartmentRepository(db)
        self.groups = GroupRepository(db)

    # ---------------------------- Users ---------------------------- #
    def get_user(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    def list_users(self, **kwargs) -> tuple[list[User], int]:
        rows, total = self.users.search(**kwargs)
        return list(rows), total

    def _unique_username(self, base: str) -> str:
        """Derive a unique, valid username from a base string (e.g. email local part)."""
        base = re.sub(r"[^A-Za-z0-9._-]", "", base) or "user"
        if len(base) < 3:
            base = f"{base}user"
        candidate = base[:80]
        i = 1
        while self.users.get_by_username(candidate):
            suffix = str(i)
            candidate = f"{base[: 80 - len(suffix)]}{suffix}"
            i += 1
        return candidate

    def create_user(
        self, data: UserCreate, base_url: Optional[str] = None
    ) -> tuple[User, Optional[str]]:
        if self.users.get_by_email(data.email):
            raise ConflictError("Email is already registered")
        if data.employee_id and self.users.get_by_employee_id(data.employee_id):
            raise ConflictError("Employee ID is already in use")
        role = self.roles.get_by_name(data.role)
        if not role:
            raise NotFoundError(f"Role '{data.role}' is not configured")
        if data.department_id and not self.departments.get(data.department_id):
            raise NotFoundError("Department not found")

        # Username is optional (login is by email). Use the supplied handle if
        # any, otherwise derive a unique one from the email address.
        raw_username = (data.username or "").strip()
        if raw_username:
            if self.users.get_by_username(raw_username):
                raise ConflictError("Username is already taken")
            username = raw_username
        else:
            username = self._unique_username(str(data.email).split("@")[0])

        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            username=username,
            email=str(data.email),
            employee_id=data.employee_id,
            department_id=data.department_id,
            role_id=role.id,
            is_active=True,
        )
        setup_token: Optional[str] = None
        if data.password:
            user.hashed_password = hash_password(data.password)
            user.status = UserStatus.ACTIVE
        else:
            user.status = UserStatus.PENDING

        self.users.add(user)
        if not data.password:
            # Record the setup token so /auth/set-password can validate it.
            setup_token = self._issue_setup_token(user)
        self.db.commit()
        if setup_token:
            email.send_password_setup_email(user, setup_token, base_url=base_url)
        # Auto-enroll the new user into all published mandatory courses.
        # Applies to every role — admins take mandatory training too.
        from app.services.assignment_service import AssignmentService
        AssignmentService(self.db).assign_mandatory_courses_to_user(user)
        return user, setup_token

    def _issue_setup_token(self, user: User) -> str:
        """Create a password-setup JWT and persist its matching token record."""
        token = create_password_setup_token(user.id)
        payload = decode_token(token)
        self.db.add(
            PasswordToken(
                user_id=user.id,
                jti=payload["jti"],
                purpose="setup",
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        )
        self.db.flush()
        return token

    def update_user(self, user_id: int, data: UserUpdate) -> User:
        user = self.get_user(user_id)
        if data.email and data.email != user.email:
            existing = self.users.get_by_email(data.email)
            if existing and existing.id != user.id:
                raise ConflictError("Email is already registered")
            user.email = str(data.email)
        if data.first_name is not None:
            user.first_name = data.first_name
        if data.last_name is not None:
            user.last_name = data.last_name
        if data.employee_id is not None and data.employee_id != user.employee_id:
            existing = self.users.get_by_employee_id(data.employee_id)
            if existing and existing.id != user.id:
                raise ConflictError("Employee ID is already in use")
            user.employee_id = data.employee_id
        if data.department_id is not None:
            if data.department_id and not self.departments.get(data.department_id):
                raise NotFoundError("Department not found")
            user.department_id = data.department_id
        if data.role is not None:
            role = self.roles.get_by_name(data.role)
            if not role:
                raise NotFoundError(f"Role '{data.role}' is not configured")
            user.role_id = role.id
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.password:
            # An admin-set password makes the account immediately usable,
            # clearing any lingering "password not set" (PENDING) state.
            user.hashed_password = hash_password(data.password)
            if user.status == UserStatus.PENDING:
                user.status = UserStatus.ACTIVE
        self.db.commit()
        return user

    def set_active(self, user_id: int, active: bool) -> User:
        user = self.get_user(user_id)
        user.is_active = active
        # Keep the visible status in sync (but never override PENDING, which
        # means the user still has to set their password).
        if active:
            if user.status == UserStatus.INACTIVE:
                user.status = UserStatus.ACTIVE
        else:
            if user.status == UserStatus.ACTIVE:
                user.status = UserStatus.INACTIVE
        self.db.commit()
        return user

    # -------------------------- Departments ------------------------ #
    def get_department(self, dept_id: int) -> Department:
        dept = self.departments.get(dept_id)
        if not dept:
            raise NotFoundError("Department not found")
        return dept

    def list_departments(self, **kwargs) -> tuple[list[Department], int]:
        rows, total = self.departments.search(**kwargs)
        return list(rows), total

    def create_department(self, data: DepartmentCreate) -> Department:
        if self.departments.get_by_name(data.name):
            raise ConflictError("Department already exists")
        dept = Department(name=data.name, description=data.description)
        self.departments.add(dept)
        self.db.commit()
        return dept

    def update_department(self, dept_id: int, data: DepartmentUpdate) -> Department:
        dept = self.get_department(dept_id)
        if data.name and data.name != dept.name:
            if self.departments.get_by_name(data.name):
                raise ConflictError("Department name already in use")
            dept.name = data.name
        if data.description is not None:
            dept.description = data.description
        if data.is_active is not None:
            dept.is_active = data.is_active
        self.db.commit()
        return dept

    def delete_department(self, dept_id: int) -> None:
        dept = self.get_department(dept_id)
        if self.users.get_by_department(dept_id):
            raise BusinessRuleError(
                "Cannot delete a department that still has members"
            )
        self.departments.delete(dept)
        self.db.commit()

    # ---------------------------- Groups --------------------------- #
    def get_group(self, group_id: int) -> Group:
        group = self.groups.get(group_id)
        if not group:
            raise NotFoundError("Group not found")
        return group

    def list_groups(self, **kwargs) -> tuple[list[Group], int]:
        rows, total = self.groups.search(**kwargs)
        return list(rows), total

    def create_group(self, data: GroupCreate) -> Group:
        if self.groups.get_by_name(data.name):
            raise ConflictError("Group already exists")
        group = Group(name=data.name, description=data.description)
        if data.member_ids:
            group.members = list(self.groups.users_by_ids(data.member_ids))
        self.groups.add(group)
        self.db.commit()
        return group

    def update_group(self, group_id: int, data: GroupUpdate) -> Group:
        group = self.get_group(group_id)
        if data.name and data.name != group.name:
            if self.groups.get_by_name(data.name):
                raise ConflictError("Group name already in use")
            group.name = data.name
        if data.description is not None:
            group.description = data.description
        if data.is_active is not None:
            group.is_active = data.is_active
        if data.member_ids is not None:
            group.members = list(self.groups.users_by_ids(data.member_ids))
        self.db.commit()
        return group

    def delete_group(self, group_id: int) -> None:
        group = self.get_group(group_id)
        self.groups.delete(group)
        self.db.commit()
