"""Generate full course content (lessons/modules) from a topic.

Complements ``quiz_generator`` (which builds a question bank from existing
material). Here Claude authors the *training material itself* from a short
topic brief, so an admin can spin up a course without uploading a document.

Like the rest of the AI layer, this degrades gracefully: with no API key a
deterministic offline generator produces a structured outline so the feature
remains demonstrable. The generated text is stored as an ordinary course
document, which means the existing quiz-generation, publishing and viewer
flows work on it unchanged.
"""
from __future__ import annotations

import re

from app.ai import claude_client
from app.ai.claude_client import ClaudeError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_SYSTEM = (
    "You are an expert corporate instructional designer. You write clear, "
    "accurate, self-contained training material that an employee can read and "
    "learn from without any external resources. You never invent statistics or "
    "cite sources that do not exist; when you give facts they are widely "
    "accepted and verifiable. You write in plain, professional prose."
)

# Keep generation bounded regardless of what the caller asks for.
MAX_MODULES = 12
MIN_MODULES = 1


def _prompt(topic: str, audience: str, module_count: int, extra: str | None) -> str:
    audience_line = f"Target audience: {audience}.\n" if audience else ""
    extra_line = f"Additional instructions: {extra}\n" if extra else ""
    return f"""Write a complete, self-contained training course on the topic below.

Topic: {topic}
{audience_line}Number of modules: {module_count}
{extra_line}
Requirements:
- Produce {module_count} modules. Each module has a short title and 2-4 lessons.
- Each lesson is 1-3 paragraphs of substantive, accurate teaching content
  (not just bullet headings). Employees must be able to learn the material by
  reading it.
- Include a brief course overview and, at the end, a short "Key takeaways" list.
- Do NOT include quiz questions — assessment is generated separately.

Return ONLY a JSON object (no prose, no markdown fences) with this shape:
{{
  "name": "concise course title (max ~80 chars)",
  "description": "1-2 sentence course summary",
  "category": "a short category label, e.g. Compliance, Safety, Technical",
  "modules": [
    {{
      "title": "Module title",
      "lessons": [
        {{ "title": "Lesson title", "content": "teaching text..." }}
      ]
    }}
  ],
  "key_takeaways": ["takeaway 1", "takeaway 2"]
}}
"""


def _render_document(data: dict, topic: str) -> str:
    """Flatten the structured course into readable plain text (stored as .txt).

    The layout doubles as the material the quiz generator reads, so headings
    stay simple and the body carries the substance.
    """
    name = (data.get("name") or topic).strip()
    description = (data.get("description") or "").strip()
    lines: list[str] = [name, "=" * len(name), ""]
    if description:
        lines += [description, ""]

    for m_idx, module in enumerate(data.get("modules", []), start=1):
        m_title = (module.get("title") or f"Module {m_idx}").strip()
        lines += [f"Module {m_idx}: {m_title}", "-" * (len(m_title) + 12), ""]
        for l_idx, lesson in enumerate(module.get("lessons", []), start=1):
            l_title = (lesson.get("title") or f"Lesson {l_idx}").strip()
            content = (lesson.get("content") or "").strip()
            lines += [f"{m_idx}.{l_idx} {l_title}", "", content, ""]

    takeaways = data.get("key_takeaways") or []
    if takeaways:
        lines += ["Key takeaways", "-------------", ""]
        lines += [f"- {t}" for t in takeaways]
        lines += [""]

    return "\n".join(lines).strip() + "\n"


def _generate_with_claude(topic: str, audience: str, module_count: int,
                          extra: str | None) -> dict:
    data = claude_client.complete_json(
        _SYSTEM, _prompt(topic, audience, module_count, extra)
    )
    if not isinstance(data, dict) or not data.get("modules"):
        raise ClaudeError("Model did not return a course object with modules")
    return data


# --------------------------------------------------------------------------- #
# Offline fallback — deterministic outline derived from the topic
# --------------------------------------------------------------------------- #
def _generate_fallback(topic: str, audience: str, module_count: int,
                       extra: str | None) -> dict:
    topic_clean = topic.strip().rstrip(".")
    aspects = [
        ("Introduction and Key Concepts",
         f"This module introduces the fundamentals of {topic_clean}. It explains "
         f"what {topic_clean} means, why it matters in the workplace, and the core "
         f"terms you will encounter throughout the course."),
        ("Policies, Standards and Responsibilities",
         f"Here we cover the standards and expectations relating to {topic_clean}, "
         f"and the responsibilities each employee holds. Understanding these helps "
         f"ensure consistent, compliant behaviour across the organisation."),
        ("Practical Application",
         f"This module walks through how {topic_clean} applies to everyday work. It "
         f"presents common situations and the recommended way to handle each, so the "
         f"guidance can be put into practice immediately."),
        ("Risks, Pitfalls and Escalation",
         f"We examine the common mistakes and risks associated with {topic_clean}, "
         f"how to recognise warning signs, and when and how to escalate a concern to "
         f"the appropriate person."),
        ("Best Practices and Continuous Improvement",
         f"The final module summarises best practices for {topic_clean} and explains "
         f"how to keep your knowledge current as policies and circumstances evolve."),
    ]
    module_count = max(MIN_MODULES, min(module_count, len(aspects)))
    modules = []
    for title, intro in aspects[:module_count]:
        modules.append({
            "title": title,
            "lessons": [
                {"title": "Overview", "content": intro},
                {
                    "title": "What this means for you",
                    "content": (
                        f"Apply the ideas in '{title.lower()}' to your own role. "
                        f"Consider how {topic_clean} shows up in your daily tasks and "
                        f"what actions you can take to align with the guidance above."
                        + (f" Note: {extra}" if extra else "")
                    ),
                },
            ],
        })
    return {
        "name": topic_clean[:80] if topic_clean else "New Course",
        "description": f"An introductory training course on {topic_clean}."
        + (f" Intended for {audience}." if audience else ""),
        "category": "General",
        "modules": modules,
        "key_takeaways": [
            f"Understand the core concepts of {topic_clean}.",
            "Know your responsibilities and the applicable standards.",
            "Recognise common risks and how to escalate concerns.",
            "Apply best practices in day-to-day work.",
        ],
    }


def generate_course(topic: str, audience: str = "", module_count: int = 4,
                    extra: str | None = None) -> tuple[dict, str, str]:
    """Generate a course.

    Returns ``(meta, content_text, source)`` where ``meta`` carries name /
    description / category, ``content_text`` is the rendered training material,
    and ``source`` is ``"ai"`` or ``"fallback"``.
    """
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("A topic is required")
    module_count = max(MIN_MODULES, min(int(module_count or 4), MAX_MODULES))

    data: dict | None = None
    source = "fallback"
    if claude_client.is_configured():
        try:
            data = _generate_with_claude(topic, audience, module_count, extra)
            source = "ai"
        except ClaudeError as exc:
            logger.warning("Claude course generation failed (%s); using fallback", exc)

    if data is None:
        data = _generate_fallback(topic, audience, module_count, extra)

    content = _render_document(data, topic)
    meta = {
        "name": (data.get("name") or topic).strip()[:200],
        "description": (data.get("description") or None),
        "category": (data.get("category") or None),
    }
    if meta["category"]:
        meta["category"] = meta["category"].strip()[:120]
    return meta, content, source
