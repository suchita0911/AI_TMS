"""Extract and clean text from uploaded training material.

Supports text documents (PDF, DOCX, PPTX, TXT) via direct extraction, and
audio/video (mp3, wav, mp4, mov, …) via local speech-to-text transcription
(faster-whisper). The resulting text — whether written or transcribed — feeds
quiz generation, so a course made of a video + a PDF is fully quizzable.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ExtractionError(Exception):
    pass


# Audio/video formats transcribed via faster-whisper (PyAV decodes the audio
# stream directly, including from video containers — no separate ffmpeg step).
_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma", ".opus"}
_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mpeg", ".mpg"}

_whisper_model = None


def _get_whisper():
    """Lazily load (and cache) the faster-whisper model. Downloaded on first use."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover
            raise ExtractionError(
                "faster-whisper is not installed; cannot transcribe audio/video"
            ) from exc
        from app.core.config import settings

        logger.info("Loading whisper model '%s' (first load may download it)…",
                    settings.WHISPER_MODEL)
        _whisper_model = WhisperModel(
            settings.WHISPER_MODEL, device="cpu", compute_type="int8"
        )
    return _whisper_model


def _transcribe_media(path: Path) -> str:
    """Transcribe speech from an audio or video file to text."""
    model = _get_whisper()
    segments, info = model.transcribe(str(path), vad_filter=True)
    logger.info("Transcribing %s (detected language=%s)…", path.name,
                getattr(info, "language", "?"))
    return " ".join(seg.text.strip() for seg in segments)


def _clean_text(text: str) -> str:
    # Normalise whitespace, collapse repeated blank lines, strip control chars.
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines).strip()


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation

    prs = Presentation(str(path))
    parts: list[str] = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
    return "\n".join(parts)


def _extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".pptx": _extract_pptx,
    ".txt": _extract_txt,
}


def is_media(filename: str) -> bool:
    """True for audio/video files (transcribed, and slow — handle in background)."""
    ext = Path(filename).suffix.lower()
    return ext in _AUDIO_EXTS or ext in _VIDEO_EXTS


def can_extract(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in _EXTRACTORS or ext in _AUDIO_EXTS or ext in _VIDEO_EXTS


def extract_text(file_path: str) -> str:
    """Extract cleaned text from a supported file (document, audio or video).

    Documents are parsed directly; audio/video are transcribed with whisper.
    Raises ExtractionError on unsupported types or extraction failure.
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    if not path.exists():
        raise ExtractionError("File not found on disk")

    is_media = ext in _AUDIO_EXTS or ext in _VIDEO_EXTS
    extractor = _EXTRACTORS.get(ext)
    if not is_media and not extractor:
        raise ExtractionError(f"No text extractor for '{ext}'")

    try:
        raw = _transcribe_media(path) if is_media else extractor(path)
    except ExtractionError:
        raise
    except Exception as exc:  # library-specific / transcription errors
        logger.exception("Text extraction failed for %s", file_path)
        raise ExtractionError(str(exc)) from exc

    cleaned = _clean_text(raw)
    if not cleaned:
        raise ExtractionError(
            "No speech detected in the media file" if is_media
            else "No readable text found in document"
        )
    return cleaned
