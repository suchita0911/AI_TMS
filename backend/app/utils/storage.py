"""Local file storage helper for course material and thumbnails."""
from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ValidationError

# Allowed upload extensions grouped by kind.
DOCUMENT_EXTS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_EXTS = DOCUMENT_EXTS | IMAGE_EXTS | AUDIO_EXTS | VIDEO_EXTS

# Extensions the AI pipeline (Phase 4) can extract text from.
TEXT_EXTRACTABLE_EXTS = {".pdf", ".docx", ".pptx", ".txt"}


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def file_kind(filename: str) -> str:
    ext = _ext(filename)
    if ext in DOCUMENT_EXTS:
        return ext.lstrip(".")
    if ext in IMAGE_EXTS:
        return "image"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    return "other"


def is_text_extractable(filename: str) -> bool:
    return _ext(filename) in TEXT_EXTRACTABLE_EXTS


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_upload(upload: UploadFile, subdir: str) -> dict:
    """Persist an UploadFile to ``UPLOAD_DIR/subdir`` and return metadata.

    Streams to disk in chunks and enforces the configured max size.
    """
    if not upload.filename:
        raise ValidationError("Uploaded file has no name")

    ext = _ext(upload.filename)
    if ext not in ALLOWED_EXTS:
        raise ValidationError(f"File type '{ext or 'unknown'}' is not allowed")

    base_dir = Path(settings.UPLOAD_DIR) / subdir
    _ensure_dir(base_dir)

    stored_name = f"{secrets.token_hex(16)}{ext}"
    dest = base_dir / stored_name

    max_bytes = settings.max_upload_bytes
    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise BusinessRuleError(
                        f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB"
                    )
                out.write(chunk)
    finally:
        upload.file.close()

    return {
        "original_filename": upload.filename,
        "stored_filename": stored_name,
        "file_path": str(dest),
        "content_type": upload.content_type,
        "file_type": file_kind(upload.filename),
        "size_bytes": size,
    }


def save_text_document(text: str, subdir: str, filename: str) -> dict:
    """Persist generated text as a .txt document and return upload-style metadata.

    Used by AI course generation, where the material is authored in-app rather
    than uploaded. The returned dict matches ``save_upload`` so a CourseDocument
    can be built from it directly.
    """
    base_dir = Path(settings.UPLOAD_DIR) / subdir
    _ensure_dir(base_dir)

    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-") or "course"
    if not safe.lower().endswith(".txt"):
        safe = f"{safe}.txt"

    stored_name = f"{secrets.token_hex(16)}.txt"
    dest = base_dir / stored_name
    data = text.encode("utf-8")
    dest.write_bytes(data)

    return {
        "original_filename": safe,
        "stored_filename": stored_name,
        "file_path": str(dest),
        "content_type": "text/plain; charset=utf-8",
        "file_type": "txt",
        "size_bytes": len(data),
    }


def save_bytes(data: bytes, subdir: str, filename: str,
               content_type: str | None = None) -> dict:
    """Persist raw bytes (e.g. a file downloaded from a link) and return
    upload-style metadata matching ``save_upload``."""
    ext = _ext(filename)
    if ext not in ALLOWED_EXTS:
        raise ValidationError(f"File type '{ext or 'unknown'}' is not allowed")
    if len(data) > settings.max_upload_bytes:
        raise BusinessRuleError(
            f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB"
        )
    base_dir = Path(settings.UPLOAD_DIR) / subdir
    _ensure_dir(base_dir)
    stored_name = f"{secrets.token_hex(16)}{ext}"
    dest = base_dir / stored_name
    dest.write_bytes(data)
    return {
        "original_filename": filename,
        "stored_filename": stored_name,
        "file_path": str(dest),
        "content_type": content_type,
        "file_type": file_kind(filename),
        "size_bytes": len(data),
    }


def delete_file(file_path: str | None) -> None:
    if not file_path:
        return
    try:
        Path(file_path).unlink(missing_ok=True)
    except OSError:
        pass
