"""Course completion certificates."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_certificate_course_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    certificate_number: Mapped[str] = mapped_column(
        String(60), unique=True, nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
