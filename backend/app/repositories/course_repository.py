"""Data access for courses and course documents."""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Course, CourseDocument
from app.models.enums import CourseStatus, CourseType
from app.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    model = Course

    def get_with_documents(self, course_id: int) -> Optional[Course]:
        return self.db.execute(
            select(Course)
            .options(selectinload(Course.documents))
            .where(Course.id == course_id)
        ).scalar_one_or_none()

    def search(
        self,
        *,
        query: Optional[str] = None,
        status: Optional[CourseStatus] = None,
        course_type: Optional[CourseType] = None,
        category: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Course], int]:
        stmt = select(Course).options(selectinload(Course.documents))
        if query:
            like = f"%{query.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Course.name).like(like),
                    func.lower(func.coalesce(Course.category, "")).like(like),
                )
            )
        if status:
            stmt = stmt.where(Course.status == status)
        if course_type:
            stmt = stmt.where(Course.course_type == course_type)
        if category:
            stmt = stmt.where(func.lower(Course.category) == category.lower())

        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.db.execute(
                stmt.order_by(Course.created_at.desc()).offset(offset).limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total

    def categories(self) -> list[str]:
        rows = self.db.execute(
            select(Course.category).where(Course.category.is_not(None)).distinct()
        ).scalars().all()
        return sorted(r for r in rows if r)


class CourseDocumentRepository(BaseRepository[CourseDocument]):
    model = CourseDocument

    def for_course(self, course_id: int) -> Sequence[CourseDocument]:
        return (
            self.db.execute(
                select(CourseDocument).where(CourseDocument.course_id == course_id)
            )
            .scalars()
            .all()
        )
