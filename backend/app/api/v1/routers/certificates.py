"""Certificate endpoints: employee issue/download + public verification."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession
from app.schemas.certificate import CertificateOut, CertificateVerify
from app.services.certificate_service import CertificateService

# Employee-facing, nested under /me/courses
me_router = APIRouter(prefix="/me/courses", tags=["Certificates"])
# Public verification endpoint (no auth) so QR codes can be scanned by anyone.
public_router = APIRouter(prefix="/certificates", tags=["Certificates"])


@me_router.get("/{course_id}/certificate", response_model=CertificateOut)
def get_certificate(course_id: int, db: DbSession, current_user: CurrentUser):
    cert = CertificateService(db).get_or_issue(course_id, current_user)
    return CertificateOut.model_validate(cert)


@me_router.get("/{course_id}/certificate/download")
def download_certificate(course_id: int, db: DbSession, current_user: CurrentUser):
    svc = CertificateService(db)
    cert = svc.get_or_issue(course_id, current_user)
    pdf = svc.render_pdf(cert)
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={cert.certificate_number}.pdf"
        },
    )


@public_router.get("/verify/{number}", response_model=CertificateVerify)
def verify_certificate(number: str, db: DbSession):
    return CertificateVerify(**CertificateService(db).verify(number))
