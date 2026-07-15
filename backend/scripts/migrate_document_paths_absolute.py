"""One-shot migration: normalise stored file paths to the portable form.

Historically ``CourseDocument.file_path`` (and ``Course.thumbnail_path``) were
stored as absolute paths, or as paths relative to the working directory that
included the storage prefix. Both break when the app moves between machines or
environments (local vs deployment). The app now stores paths *relative to the
upload base* (e.g. ``courses/1/ab12.txt``) and resolves them against the current
``UPLOAD_DIR`` at read time, so the same value works everywhere.

This backfills existing rows to that portable form. It's idempotent and only
rewrites values it can locate on disk; anything it can't find is reported and
left untouched.

Run from the backend/ directory:

    PYTHONPATH=. .venv/Scripts/python.exe scripts/migrate_document_paths_absolute.py
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.course import Course, CourseDocument
from app.utils import storage


def _to_relative(value: str) -> tuple[str | None, str]:
    """Return (new_relative_value, status) for a stored path value."""
    base = settings.upload_path
    resolved = storage.resolve_path(value)
    if resolved is None:
        return None, "empty"
    if not resolved.is_file():
        return None, "missing"
    try:
        rel = resolved.resolve().relative_to(base).as_posix()
    except ValueError:
        # File exists but lives outside the upload base — can't make portable.
        return None, "outside-base"
    return rel, "ok"


def main() -> None:
    print(f"upload base: {settings.upload_path}")
    db = SessionLocal()
    try:
        updated = unchanged = missing = other = 0

        for d in db.query(CourseDocument).all():
            if not d.file_path:
                continue
            rel, status = _to_relative(d.file_path)
            if status == "ok":
                if rel != d.file_path:
                    d.file_path = rel
                    updated += 1
                else:
                    unchanged += 1
            elif status == "missing":
                missing += 1
                print(f"  ! doc {d.id}: file not found ({d.file_path!r})")
            else:
                other += 1
                print(f"  ? doc {d.id}: {status} ({d.file_path!r})")

        for c in db.query(Course).filter(Course.thumbnail_path.isnot(None)).all():
            rel, status = _to_relative(c.thumbnail_path)
            if status == "ok" and rel != c.thumbnail_path:
                c.thumbnail_path = rel
                updated += 1
            elif status == "missing":
                missing += 1
                print(f"  ! course {c.id} thumbnail not found ({c.thumbnail_path!r})")

        db.commit()
        print(f"done: {updated} updated, {unchanged} already portable, "
              f"{missing} missing, {other} skipped (left unchanged)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
