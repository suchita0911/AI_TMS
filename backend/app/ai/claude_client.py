"""Thin wrapper around the Anthropic Claude API.

All AI features degrade gracefully: if no API key is configured the caller can
fall back to a deterministic, document-grounded generator so the system remains
fully functional offline.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ClaudeError(Exception):
    pass


def is_configured() -> bool:
    key = settings.ANTHROPIC_API_KEY or ""
    return bool(key) and not key.startswith("sk-ant-xxxx")


def _client():
    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover
        raise ClaudeError("anthropic SDK not installed") from exc
    return Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def complete(system: str, user: str, max_tokens: int | None = None,
             model: str | None = None) -> str:
    """Send a single-turn message and return the text response.

    ``model`` overrides the default (e.g. a faster model for structured tasks).
    """
    if not is_configured():
        raise ClaudeError("ANTHROPIC_API_KEY is not configured")
    client = _client()
    try:
        resp = client.messages.create(
            model=model or settings.CLAUDE_MODEL,
            max_tokens=max_tokens or settings.CLAUDE_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as exc:  # network / auth / rate-limit
        logger.exception("Claude API call failed")
        raise ClaudeError(str(exc)) from exc

    parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
    return "\n".join(parts).strip()


def complete_json(system: str, user: str, max_tokens: int | None = None,
                  model: str | None = None) -> Any:
    """Call the model and parse a JSON array/object from the response."""
    raw = complete(system, user, max_tokens, model)
    return _parse_json(raw)


def _parse_json(raw: str) -> Any:
    raw = raw.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Best-effort: extract the first JSON array/object substring
        match = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ClaudeError("Model did not return valid JSON")
