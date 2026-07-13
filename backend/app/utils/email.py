"""Email sending via Brevo's HTTP API or SMTP.

Delivery backend is chosen at call time (see :func:`send_email`):
  1. Brevo HTTP API  — when ``BREVO_API_KEY`` is set (works where outbound SMTP
     is blocked, e.g. Render).
  2. SMTP            — when ``SMTP_HOST`` is set (local dev / SMTP-friendly hosts).
No-op ("skipped") when neither is configured.
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def is_configured() -> bool:
    return bool(settings.BREVO_API_KEY or settings.SMTP_HOST)


def send_password_setup_email(user, token: str, base_url: str | None = None) -> str:
    """Email a (new) user a one-time link to set their password.

    Shared by self-registration and admin user-creation. ``base_url`` is the
    origin the request came in on (so the link works over a shared tunnel);
    it falls back to the configured ``FRONTEND_BASE_URL``. Returns the delivery
    status from :func:`send_email` ('sent' | 'failed' | 'skipped').
    """
    base = (base_url or settings.FRONTEND_BASE_URL).rstrip("/")
    link = f"{base}/set-password?token={token}"
    hours = settings.PASSWORD_SETUP_TOKEN_EXPIRE_HOURS
    subject = f"Set your password for {settings.APP_NAME}"
    text = (
        f"Hi {user.first_name},\n\n"
        f"An account has been created for you on {settings.APP_NAME}. "
        f"Open the link below to set your password and sign in "
        f"(valid for {hours} hours):\n\n{link}\n"
    )
    html = (
        f"<p>Hi {user.first_name},</p>"
        f"<p>An account has been created for you on <b>{settings.APP_NAME}</b>. "
        f"Click the button below to set your password and sign in "
        f"(this link is valid for {hours} hours):</p>"
        f'<p><a href="{link}" '
        f'style="display:inline-block;padding:10px 18px;background:#4f46e5;'
        f'color:#fff;border-radius:6px;text-decoration:none">Set password</a></p>'
        f'<p>Or paste this link into your browser:<br><a href="{link}">{link}</a></p>'
    )
    return send_email(user.email, subject, html, text)


def send_email(to: str, subject: str, body_html: str, body_text: str | None = None) -> str:
    """Return delivery status: 'sent' | 'failed' | 'skipped'.

    Prefers the Brevo HTTP API (works where outbound SMTP is blocked); falls
    back to SMTP; no-ops when neither backend is configured.
    """
    if settings.BREVO_API_KEY:
        return _send_via_brevo(to, subject, body_html, body_text)
    if settings.SMTP_HOST:
        return _send_via_smtp(to, subject, body_html, body_text)
    logger.info("Email not configured; skipping email to %s (%s)", to, subject)
    return "skipped"


def _send_via_brevo(to: str, subject: str, body_html: str, body_text: str | None) -> str:
    """Send through Brevo's transactional email HTTP API (over HTTPS)."""
    sender_name, sender_email = parseaddr(settings.SMTP_FROM)
    payload = {
        "sender": {"email": sender_email, "name": sender_name or sender_email},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": body_html,
    }
    if body_text:
        payload["textContent"] = body_text
    try:
        resp = httpx.post(
            settings.BREVO_API_URL,
            headers={
                "api-key": settings.BREVO_API_KEY,
                "accept": "application/json",
                "content-type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if resp.status_code in (200, 201, 202):
            return "sent"
        logger.warning("Email to %s failed via Brevo: HTTP %s %s",
                       to, resp.status_code, resp.text[:300])
        return "failed"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email to %s failed via Brevo: %s", to, exc)
        return "failed"


def _send_via_smtp(to: str, subject: str, body_html: str, body_text: str | None) -> str:
    """Send through an SMTP server (local dev / SMTP-friendly hosts)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to
        msg.attach(MIMEText(body_text or "", "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [to], msg.as_string())
        return "sent"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email to %s failed: %s", to, exc)
        return "failed"
