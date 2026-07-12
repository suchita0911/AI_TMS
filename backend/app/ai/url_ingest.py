"""Fetch course material from a URL.

Two kinds of links are supported:
- a **web page** (text/html) → the readable text is extracted, and
- a **direct file** (PDF, DOCX, PPTX, TXT, or audio/video) → the file is
  downloaded so the normal extraction/transcription pipeline can process it.

A basic SSRF guard rejects non-http(s) URLs and hosts that resolve to private,
loopback, link-local or reserved addresses.
"""
from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
from lxml import html as lxml_html

from app.core.exceptions import BusinessRuleError, ValidationError
from app.core.logging_config import get_logger
from app.utils import storage

logger = get_logger(__name__)

_MAX_BYTES = 30 * 1024 * 1024  # cap on fetched content
_TIMEOUT = 30.0

# Map common content types to a file extension when the URL has none.
_CT_EXT = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-matroska": ".mkv",
}


def _guard(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError("Only http(s) links are supported")
    host = parsed.hostname
    if not host:
        raise ValidationError("Invalid URL")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise BusinessRuleError("Could not resolve the link's host") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValidationError("That URL is not allowed")


def _extract_html(content: bytes) -> tuple[str, str]:
    """Return (title, readable_text) from an HTML page."""
    doc = lxml_html.fromstring(content)
    title = (doc.findtext(".//title") or "").strip()
    for bad in doc.xpath("//script | //style | //noscript | //nav | //footer | //header | //form"):
        parent = bad.getparent()
        if parent is not None:
            parent.remove(bad)
    text = doc.text_content()
    return title, text


def fetch(url: str) -> dict:
    """Fetch a URL. Returns either
    {'kind': 'html', 'title', 'text', 'url'} or
    {'kind': 'file', 'data', 'filename', 'content_type', 'url'}.
    """
    url = (url or "").strip()
    _guard(url)
    try:
        with httpx.Client(follow_redirects=True, timeout=_TIMEOUT,
                          headers={"User-Agent": "AI-TMS/1.0 (+course-material)"}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.content
    except httpx.HTTPError as exc:
        raise BusinessRuleError(f"Could not fetch the link: {exc}") from exc

    if len(data) > _MAX_BYTES:
        raise BusinessRuleError("Linked content is too large")

    content_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    path = urlparse(str(resp.url)).path
    ext = Path(unquote(path)).suffix.lower()

    # Web page → extract readable text.
    if content_type == "text/html" or (not ext and content_type.startswith("text/html")):
        title, text = _extract_html(data)
        if not text.strip():
            raise BusinessRuleError("No readable text found at that link")
        return {"kind": "html", "title": title or url, "text": text, "url": url}

    # Direct file → download for the normal pipeline.
    if ext not in storage.ALLOWED_EXTS:
        ext = _CT_EXT.get(content_type, ext)
    if ext not in storage.ALLOWED_EXTS:
        raise ValidationError(
            f"Unsupported link content ({content_type or ext or 'unknown'}). "
            "Provide a web page or a direct file link (PDF, DOCX, PPTX, TXT, audio or video)."
        )
    name = Path(unquote(path)).name
    if not name or not name.lower().endswith(ext):
        name = f"{(name or 'download')}{ext}"
    return {"kind": "file", "data": data, "filename": name,
            "content_type": content_type, "url": url}
