"""Validate AI-generated questions before they enter the question bank."""
from __future__ import annotations

from app.models.enums import DifficultyLevel, QuestionType

_VALID_TYPES = {t.value for t in QuestionType}
_VALID_DIFF = {d.value for d in DifficultyLevel}


class ValidationReport:
    def __init__(self):
        self.valid: list[dict] = []
        self.rejected: list[tuple[dict, str]] = []

    def accept(self, q: dict) -> None:
        self.valid.append(q)

    def reject(self, q: dict, reason: str) -> None:
        self.rejected.append((q, reason))


def _normalise(s) -> str:
    return str(s).strip().lower()


def validate_question(q: dict) -> tuple[bool, str]:
    """Return (is_valid, reason). Enforces the structural rules from the spec."""
    if not isinstance(q, dict):
        return False, "not an object"

    qtype = _normalise(q.get("question_type"))
    if qtype not in _VALID_TYPES:
        return False, f"invalid question_type '{q.get('question_type')}'"

    diff = _normalise(q.get("difficulty"))
    if diff not in _VALID_DIFF:
        return False, f"invalid difficulty '{q.get('difficulty')}'"

    text = (q.get("question_text") or "").strip()
    if len(text) < 8:
        return False, "question text too short"

    options = q.get("options")
    if not isinstance(options, list):
        return False, "options must be a list"

    # Deduplicate/normalise options
    opts = [str(o).strip() for o in options if str(o).strip()]
    if len(set(_normalise(o) for o in opts)) != len(opts):
        return False, "duplicate options"

    if qtype == QuestionType.TRUE_FALSE.value:
        if len(opts) != 2:
            return False, "true/false must have exactly 2 options"
    else:
        if len(opts) != 4:
            return False, f"{qtype} must have exactly 4 options"

    correct = (q.get("correct_answer") or "").strip()
    if not correct:
        return False, "missing correct_answer"
    # The correct answer must be present among the options (grounding check)
    if _normalise(correct) not in {_normalise(o) for o in opts}:
        return False, "correct_answer not among options"

    return True, "ok"


def validate_batch(questions: list[dict]) -> ValidationReport:
    report = ValidationReport()
    seen_texts: set[str] = set()
    for q in questions:
        ok, reason = validate_question(q)
        if not ok:
            report.reject(q, reason)
            continue
        key = _normalise(q.get("question_text"))
        if key in seen_texts:
            report.reject(q, "duplicate question")
            continue
        seen_texts.add(key)
        # Normalise fields onto the accepted question
        q["question_type"] = _normalise(q["question_type"])
        q["difficulty"] = _normalise(q["difficulty"])
        q["options"] = [str(o).strip() for o in q["options"] if str(o).strip()]
        q["correct_answer"] = str(q["correct_answer"]).strip()
        report.accept(q)
    return report
