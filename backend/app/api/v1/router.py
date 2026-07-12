"""Aggregate all v1 routers."""
from fastapi import APIRouter

from app.api.v1.routers import (
    auth,
    certificates,
    courses,
    departments,
    groups,
    me,
    notifications,
    reports,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(departments.router)
api_router.include_router(groups.router)
api_router.include_router(courses.router)
api_router.include_router(courses.admin_router)
api_router.include_router(me.router)
api_router.include_router(me.quiz_router)
api_router.include_router(reports.router)
api_router.include_router(reports.me_router)
api_router.include_router(notifications.router)
api_router.include_router(notifications.admin_router)
api_router.include_router(certificates.me_router)
api_router.include_router(certificates.public_router)
