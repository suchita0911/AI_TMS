"""Generate a question bank from course material.

Uses Claude when configured; otherwise falls back to a deterministic generator
that derives questions strictly from sentences in the material (so questions are
always grounded in the uploaded documents and never hallucinated).
"""
from __future__ import annotations

import re

from app.ai import claude_client
from app.ai.claude_client import ClaudeError
from app.ai.question_validator import validate_batch
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.enums import DifficultyLevel, QuestionType

logger = get_logger(__name__)

# Target difficulty mix (matches the spec's 4:4:2 example → 40/40/20).
DIFFICULTY_MIX = {
    DifficultyLevel.EASY: 0.4,
    DifficultyLevel.MEDIUM: 0.4,
    DifficultyLevel.HARD: 0.2,
}

_SYSTEM = (
    "You are an expert instructional designer creating assessment questions for "
    "corporate compliance and training courses. You ONLY use facts explicitly present "
    "in the provided training material. You never invent information. If a fact is not "
    "in the material, you do not write a question about it."
)


def _batch_prompt(material: str, count: int, avoid: list[str] | None = None,
                  subject: str | None = None) -> str:
    avoid_block = ""
    if avoid:
        joined = "\n".join(f"- {q}" for q in avoid[-40:])
        avoid_block = (
            "\n\nDo NOT repeat or paraphrase any of these already-created questions:\n"
            f"{joined}\n"
        )
    subject_block = ""
    if subject:
        subject_block = (
            f"\nCOURSE SUBJECT: \"{subject}\"\n"
            "Only write questions that are RELEVANT to this course subject. The "
            "material may contain unrelated or off-topic passages (e.g. from other "
            "courses) — IGNORE any content that is not about the course subject and "
            "do NOT write questions about it. If a passage is off-topic, skip it.\n"
        )
    return f"""Using ONLY the training material below, write {count} quiz questions.
{subject_block}
Rules:
- Every question and its correct answer MUST be verifiable from the material.
- Every question MUST be on the course subject above; discard off-topic material.
- Mix question types: "mcq" (4 options), "true_false" (2 options: "True","False"), "scenario" (4 options).
- Mix difficulty: roughly 40% "easy", 40% "medium", 20% "hard".
- For each question provide: question_type, difficulty, question_text, options (array),
  correct_answer (must exactly match one option), explanation, topic, reference_section
  (a short phrase quoted from the material).
- Make every question distinct; cover different facts across the material.
- Return ONLY a JSON array of objects. No prose, no markdown.{avoid_block}

TRAINING MATERIAL:
\"\"\"
{material[:12000]}
\"\"\"
"""


def _generate_with_claude(material: str, count: int, subject: str | None = None) -> list[dict]:
    collected: list[dict] = []
    seen: set[str] = set()
    batch = 25
    attempts = 0
    # Bound total attempts so a request can never run unbounded.
    max_attempts = min(8, (count // batch) + 3)
    while len(collected) < count and attempts < max_attempts:
        attempts += 1
        need = min(batch, count - len(collected) + 5)
        avoid = [q["question_text"] for q in collected]
        try:
            data = claude_client.complete_json(
                _SYSTEM, _batch_prompt(material, need, avoid, subject),
                model=settings.CLAUDE_QUIZ_MODEL,
            )
        except ClaudeError:
            raise
        if isinstance(data, dict):
            data = data.get("questions", [])
        report = validate_batch(list(data))
        # Cross-batch dedup so repeated questions don't waste subsequent calls.
        added = 0
        for q in report.valid:
            key = q["question_text"].strip().lower()
            if key in seen:
                continue
            seen.add(key)
            collected.append(q)
            added += 1
        logger.info("Claude batch %s: +%s new (%s rejected)", attempts, added, len(report.rejected))
        if added == 0:
            break  # material exhausted — stop rather than burn API calls
    return collected[:count]


# --------------------------------------------------------------------------- #
# Offline fallback — deterministic, grounded in the document sentences
# --------------------------------------------------------------------------- #
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "must", "will", "are",
    "was", "were", "has", "have", "not", "you", "your", "may", "can", "all",
    "any", "into", "within", "which", "their", "they", "them", "a", "an", "of",
    "to", "in", "on", "is", "be", "as", "or", "by", "it",
}


def _sentences(material: str) -> list[str]:
    raw = [s.strip() for s in _SENT_SPLIT.split(material.replace("\n", " ")) if s.strip()]
    return [s for s in raw if 30 <= len(s) <= 220]


def _keywords(sentence: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", sentence)
    # Prefer capitalised or long words as answer candidates.
    cands = [w for w in words if w.lower() not in _STOPWORDS]
    cands.sort(key=lambda w: (w[0].isupper(), len(w)), reverse=True)
    return cands


def _difficulty_for(index: int) -> str:
    r = index % 10
    if r < 4:
        return DifficultyLevel.EASY.value
    if r < 8:
        return DifficultyLevel.MEDIUM.value
    return DifficultyLevel.HARD.value


def _subject_filter(sentences: list[str], subject: str | None, count: int) -> list[str]:
    """Keep only sentences relevant to the subject (share a keyword).

    Offline counterpart to the AI prompt's topic-scoping. If filtering would
    starve generation (too few matches), fall back to all sentences so we never
    produce zero questions.
    """
    if not subject:
        return sentences
    subj_words = {w.lower() for w in _keywords(subject)}
    if not subj_words:
        return sentences
    relevant = [s for s in sentences if subj_words & {w.lower() for w in _keywords(s)}]
    if len(relevant) >= max(count, 3):
        return relevant
    return relevant or sentences


def _generate_fallback(material: str, count: int, subject: str | None = None) -> list[dict]:
    sentences = _subject_filter(_sentences(material), subject, count)
    if not sentences:
        return []
    all_keywords = list({k for s in sentences for k in _keywords(s)})
    questions: list[dict] = []
    idx = 0
    for s in sentences:
        if len(questions) >= count:
            break
        kws = _keywords(s)
        difficulty = _difficulty_for(idx)
        if kws and len(all_keywords) >= 4 and idx % 2 == 0:
            answer = kws[0]
            distractors = [w for w in all_keywords if w.lower() != answer.lower()][:3]
            if len(distractors) < 3:
                idx += 1
                continue
            blanked = re.sub(re.escape(answer), "_____", s, count=1)
            options = distractors + [answer]
            # deterministic shuffle by rotating on idx
            rot = idx % 4
            options = options[rot:] + options[:rot]
            questions.append({
                "question_type": QuestionType.MCQ.value,
                "difficulty": difficulty,
                "question_text": f"Fill in the blank: {blanked}",
                "options": options,
                "correct_answer": answer,
                "explanation": f"Based on the material: \"{s}\"",
                "topic": kws[0] if kws else "General",
                "reference_section": s[:120],
            })
        else:
            # True/False — half true (verbatim), half altered to false.
            make_false = idx % 2 == 1 and kws
            if make_false:
                altered = re.sub(re.escape(kws[0]), "no " + kws[0], s, count=1)
                questions.append({
                    "question_type": QuestionType.TRUE_FALSE.value,
                    "difficulty": difficulty,
                    "question_text": f"True or False: {altered}",
                    "options": ["True", "False"],
                    "correct_answer": "False",
                    "explanation": f"The material states: \"{s}\"",
                    "topic": (kws[0] if kws else "General"),
                    "reference_section": s[:120],
                })
            else:
                questions.append({
                    "question_type": QuestionType.TRUE_FALSE.value,
                    "difficulty": difficulty,
                    "question_text": f"True or False: {s}",
                    "options": ["True", "False"],
                    "correct_answer": "True",
                    "explanation": f"This statement appears in the material.",
                    "topic": (kws[0] if kws else "General"),
                    "reference_section": s[:120],
                })
        idx += 1

    report = validate_batch(questions)
    return report.valid[:count]


def generate_questions(material: str, count: int,
                       subject: str | None = None) -> tuple[list[dict], str]:
    """Return (questions, source) where source is 'ai' or 'fallback'.

    ``subject`` scopes generation to the course topic so questions stay relevant
    even when the uploaded material contains off-topic passages.
    """
    material = (material or "").strip()
    if not material:
        return [], "none"

    if claude_client.is_configured():
        try:
            questions = _generate_with_claude(material, count, subject)
            if questions:
                return questions, "ai"
            logger.warning("Claude produced no valid questions; using fallback")
        except ClaudeError as exc:
            logger.warning("Claude generation failed (%s); using fallback", exc)

    return _generate_fallback(material, count, subject), "fallback"
