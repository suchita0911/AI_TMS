"""Generic repository with common CRUD helpers."""
from __future__ import annotations

from typing import Generic, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: Type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, id_: int) -> ModelT | None:
        return self.db.get(self.model, id_)

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelT]:
        stmt = select(self.model).offset(offset).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def count(self) -> int:
        return self.db.execute(select(func.count()).select_from(self.model)).scalar_one()

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()
