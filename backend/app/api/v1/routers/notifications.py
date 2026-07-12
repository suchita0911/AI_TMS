"""Notification endpoints: employee inbox + admin reminder trigger."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, require_admin
from app.schemas.common import Message
from app.schemas.notification import NotificationOut, ReminderRunResult, UnreadCount
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/me/notifications", tags=["Notifications"])
admin_router = APIRouter(
    prefix="/notifications", tags=["Notifications"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=list[NotificationOut])
def list_notifications(db: DbSession, current_user: CurrentUser,
                       unread_only: bool = Query(False)):
    items = NotificationService(db).list_for(current_user, unread_only=unread_only)
    return [NotificationOut.model_validate(n) for n in items]


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(db: DbSession, current_user: CurrentUser):
    return UnreadCount(unread=NotificationService(db).unread_count(current_user))


@router.post("/{notification_id}/read", response_model=Message)
def mark_read(notification_id: int, db: DbSession, current_user: CurrentUser):
    NotificationService(db).mark_read(notification_id, current_user)
    return Message(detail="Marked as read")


@router.post("/read-all", response_model=Message)
def mark_all_read(db: DbSession, current_user: CurrentUser):
    n = NotificationService(db).mark_all_read(current_user)
    return Message(detail=f"Marked {n} notifications as read")


@admin_router.post("/run-reminders", response_model=ReminderRunResult)
def run_reminders(db: DbSession, current_user: CurrentUser):
    return ReminderRunResult(**NotificationService(db).generate_reminders())
