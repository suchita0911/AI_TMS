"""Data access for users, roles, departments and groups."""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import RoleName
from app.models.user import Department, Group, Role, User
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    model = Role

    def get_by_name(self, name: RoleName) -> Optional[Role]:
        return self.db.execute(
            select(Role).where(Role.name == name)
        ).scalar_one_or_none()


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.execute(
            select(User).where(func.lower(User.username) == username.lower())
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        ).scalar_one_or_none()

    def get_by_employee_id(self, employee_id: str) -> Optional[User]:
        return self.db.execute(
            select(User).where(func.lower(User.employee_id) == employee_id.lower())
        ).scalar_one_or_none()

    def search(
        self,
        *,
        query: Optional[str] = None,
        role: Optional[RoleName] = None,
        department_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[User], int]:
        stmt = select(User).join(Role)
        if query:
            like = f"%{query.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(User.first_name).like(like),
                    func.lower(User.last_name).like(like),
                    func.lower(User.username).like(like),
                    func.lower(User.email).like(like),
                    func.lower(func.coalesce(User.employee_id, "")).like(like),
                )
            )
        if role:
            stmt = stmt.where(Role.name == role)
        if department_id is not None:
            stmt = stmt.where(User.department_id == department_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.db.execute(
                stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total

    def get_by_department(self, department_id: int) -> Sequence[User]:
        return (
            self.db.execute(select(User).where(User.department_id == department_id))
            .scalars()
            .all()
        )


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    def get_by_name(self, name: str) -> Optional[Department]:
        return self.db.execute(
            select(Department).where(func.lower(Department.name) == name.lower())
        ).scalar_one_or_none()

    def search(
        self, *, query: Optional[str] = None, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[Department], int]:
        stmt = select(Department)
        if query:
            stmt = stmt.where(func.lower(Department.name).like(f"%{query.lower()}%"))
        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.db.execute(stmt.order_by(Department.name).offset(offset).limit(limit))
            .scalars()
            .all()
        )
        return rows, total


class GroupRepository(BaseRepository[Group]):
    model = Group

    def get_by_name(self, name: str) -> Optional[Group]:
        return self.db.execute(
            select(Group).where(func.lower(Group.name) == name.lower())
        ).scalar_one_or_none()

    def search(
        self, *, query: Optional[str] = None, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[Group], int]:
        stmt = select(Group)
        if query:
            stmt = stmt.where(func.lower(Group.name).like(f"%{query.lower()}%"))
        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.db.execute(stmt.order_by(Group.name).offset(offset).limit(limit))
            .scalars()
            .all()
        )
        return rows, total

    def users_by_ids(self, ids: list[int]) -> Sequence[User]:
        if not ids:
            return []
        return (
            self.db.execute(select(User).where(User.id.in_(ids))).scalars().all()
        )
