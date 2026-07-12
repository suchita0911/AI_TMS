"""Notification schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    message: str
    course_id: Optional[int]
    is_read: bool
    email_status: str
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int


class ReminderRunResult(BaseModel):
    reminders_created: int
    checked: int
