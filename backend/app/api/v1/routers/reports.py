"""Reporting & analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession, require_admin
from app.services.report_service import ReportService
from app.utils import report_export

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(require_admin)])
me_router = APIRouter(prefix="/me", tags=["My Courses"])


@router.get("/overview")
def overview(db: DbSession, current_user: CurrentUser):
    return ReportService(db).overview()


@router.get("/departments")
def departments(db: DbSession, current_user: CurrentUser):
    return ReportService(db).department_completion()


@router.get("/employees")
def employees(db: DbSession, current_user: CurrentUser):
    return ReportService(db).employee_progress()


@router.get("/trend")
def trend(db: DbSession, current_user: CurrentUser, months: int = Query(6, ge=1, le=24)):
    return ReportService(db).completion_trend(months)


def _report_sections(svc: ReportService):
    ov = svc.overview()
    return {
        "Overview": (
            ["Metric", "Value"],
            [[k.replace("_", " ").title(), v] for k, v in ov.items()],
        ),
        "Departments": (
            ["Department", "Total", "Completed", "Completion %"],
            [[d["department"], d["total"], d["completed"], d["completion_rate"]]
             for d in svc.department_completion()],
        ),
        "Employees": (
            ["Name", "Email", "Department", "Assigned", "Completed", "Completion %", "Avg Score"],
            [[e["name"], e["email"], e["department"] or "-", e["assigned"], e["completed"],
              e["completion_rate"], e["average_score"] if e["average_score"] is not None else "-"]
             for e in svc.employee_progress()],
        ),
    }


@router.get("/export/excel")
def export_excel(db: DbSession, current_user: CurrentUser):
    data = report_export.build_excel(_report_sections(ReportService(db)))
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tms_report.xlsx"},
    )


@router.get("/export/pdf")
def export_pdf(db: DbSession, current_user: CurrentUser):
    data = report_export.build_pdf("AI TMS — Training Report", _report_sections(ReportService(db)))
    return StreamingResponse(
        iter([data]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tms_report.pdf"},
    )


@me_router.get("/report")
def my_report(db: DbSession, current_user: CurrentUser):
    return ReportService(db).my_report(current_user)
