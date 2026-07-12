"""Certificate issuance & verification (Phase 9)."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.models.certificate import Certificate
from app.models.course import Course, EmployeeCourseStatus
from app.models.enums import EnrollmentStatus
from app.models.user import User
from app.repositories.enrollment_repository import EnrollmentRepository
from app.utils import certificate_pdf


class CertificateService:
    def __init__(self, db: Session):
        self.db = db
        self.enrollments = EnrollmentRepository(db)

    def _gen_number(self, course_id: int, user_id: int) -> str:
        year = datetime.now(timezone.utc).year
        return f"TMS-{year}-{course_id:04d}-{user_id:04d}-{secrets.token_hex(3).upper()}"

    def get_or_issue(self, course_id: int, user: User) -> Certificate:
        enrollment = self.enrollments.get_for(course_id, user.id)
        if not enrollment:
            raise PermissionDeniedError("This course is not assigned to you")
        if enrollment.status != EnrollmentStatus.COMPLETED:
            raise BusinessRuleError(
                "Certificate is available only after completing the course and passing the quiz"
            )

        existing = self.db.execute(
            select(Certificate).where(
                Certificate.course_id == course_id, Certificate.user_id == user.id
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        cert = Certificate(
            certificate_number=self._gen_number(course_id, user.id),
            course_id=course_id,
            user_id=user.id,
            score=enrollment.best_score,
            issued_at=datetime.now(timezone.utc),
        )
        self.db.add(cert)
        self.db.commit()
        return cert

    def render_pdf(self, cert: Certificate) -> bytes:
        course = self.db.get(Course, cert.course_id)
        user = self.db.get(User, cert.user_id)
        verify_url = f"{settings.FRONTEND_BASE_URL}/verify/{cert.certificate_number}"
        return certificate_pdf.build_certificate_pdf(
            employee_name=user.full_name if user else "Employee",
            course_name=course.name if course else "Course",
            completion_date=cert.issued_at.strftime("%d %B %Y"),
            certificate_number=cert.certificate_number,
            score=float(cert.score) if cert.score is not None else None,
            verify_url=verify_url,
        )

    def verify(self, number: str) -> dict:
        cert = self.db.execute(
            select(Certificate).where(Certificate.certificate_number == number)
        ).scalar_one_or_none()
        if not cert:
            return {"valid": False}
        course = self.db.get(Course, cert.course_id)
        user = self.db.get(User, cert.user_id)
        return {
            "valid": True,
            "certificate_number": cert.certificate_number,
            "employee_name": user.full_name if user else None,
            "course_name": course.name if course else None,
            "score": float(cert.score) if cert.score is not None else None,
            "issued_at": cert.issued_at,
        }

    def get_cert(self, course_id: int, user: User) -> Certificate:
        cert = self.db.execute(
            select(Certificate).where(
                Certificate.course_id == course_id, Certificate.user_id == user.id
            )
        ).scalar_one_or_none()
        if not cert:
            raise NotFoundError("Certificate not found")
        return cert
