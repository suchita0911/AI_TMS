"""Lightweight in-process scheduler for due-date reminders.

Runs an asyncio background loop that periodically invokes the notification
service's reminder generation. No external dependency (APScheduler/cron) is
required; the reminder logic itself is idempotent per day, so re-running within
the same day never produces duplicate notifications or emails.
"""
from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging_config import get_logger
from app.services.notification_service import NotificationService

logger = get_logger(__name__)


def _run_reminders_once() -> None:
    """Open a fresh session, generate reminders, and log the outcome."""
    db = SessionLocal()
    try:
        result = NotificationService(db).generate_reminders()
        logger.info(
            "Due-date reminders: created=%s checked=%s",
            result.get("reminders_created"), result.get("checked"),
        )
    except Exception:  # noqa: BLE001 - never let the loop die on one bad run
        logger.exception("Due-date reminder run failed")
    finally:
        db.close()


async def reminder_loop() -> None:
    """Run reminders on startup, then every REMINDER_INTERVAL_HOURS."""
    interval = max(1, settings.REMINDER_INTERVAL_HOURS) * 3600
    logger.info("Reminder scheduler started (every %sh)", settings.REMINDER_INTERVAL_HOURS)
    while True:
        # Run the (blocking) DB work off the event loop so we don't stall it.
        await asyncio.to_thread(_run_reminders_once)
        await asyncio.sleep(interval)
