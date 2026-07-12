"""Data access for the question bank."""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.enums import DifficultyLevel, QuestionType
from app.models.question import QuestionBank
from app.repositories.base import BaseRepository


class QuestionBankRepository(BaseRepository[QuestionBank]):
    model = QuestionBank

    def for_course(
        self,
        course_id: int,
        *,
        difficulty: Optional[DifficultyLevel] = None,
        question_type: Optional[QuestionType] = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[QuestionBank], int]:
        stmt = select(QuestionBank).where(QuestionBank.course_id == course_id)
        if active_only:
            stmt = stmt.where(QuestionBank.is_active.is_(True))
        if difficulty:
            stmt = stmt.where(QuestionBank.difficulty == difficulty)
        if question_type:
            stmt = stmt.where(QuestionBank.question_type == question_type)
        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        rows = (
            self.db.execute(
                stmt.order_by(QuestionBank.difficulty, QuestionBank.id)
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total

    def all_active(self, course_id: int) -> Sequence[QuestionBank]:
        return (
            self.db.execute(
                select(QuestionBank).where(
                    QuestionBank.course_id == course_id,
                    QuestionBank.is_active.is_(True),
                )
            )
            .scalars()
            .all()
        )

    def existing_texts(self, course_id: int) -> set[str]:
        rows = self.db.execute(
            select(QuestionBank.question_text).where(QuestionBank.course_id == course_id)
        ).scalars().all()
        return {t.strip().lower() for t in rows}

    def count(self, course_id: int) -> int:
        return self.db.execute(
            select(func.count()).select_from(QuestionBank).where(
                QuestionBank.course_id == course_id, QuestionBank.is_active.is_(True)
            )
        ).scalar_one()

    def group_counts(self, course_id: int, column) -> dict[str, int]:
        rows = self.db.execute(
            select(column, func.count())
            .where(QuestionBank.course_id == course_id, QuestionBank.is_active.is_(True))
            .group_by(column)
        ).all()
        out: dict[str, int] = {}
        for key, n in rows:
            out[key.value if hasattr(key, "value") else str(key)] = n
        return out

    def clear_course(self, course_id: int) -> int:
        result = self.db.execute(
            delete(QuestionBank).where(QuestionBank.course_id == course_id)
        )
        return result.rowcount or 0
