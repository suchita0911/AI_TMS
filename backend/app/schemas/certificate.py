"""Certificate schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    certificate_number: str
    course_id: int
    score: Optional[float]
    issued_at: datetime


class CertificateVerify(BaseModel):
    valid: bool
    certificate_number: Optional[str] = None
    employee_name: Optional[str] = None
    course_name: Optional[str] = None
    score: Optional[float] = None
    issued_at: Optional[datetime] = None
