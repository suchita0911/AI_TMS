"""Lightweight audit-log writer used across services."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.auth import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        action: str,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str | int] = None,
        detail: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            detail=detail,
            ip_address=ip_address,
            success=success,
        )
        self.db.add(log)
        self.db.flush()
        return log
