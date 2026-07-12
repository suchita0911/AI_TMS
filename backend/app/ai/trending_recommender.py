"""Recommend trending, high-value training topics for an IT organisation.

Helps an admin decide *what* to roll out next: given the current catalogue (to
avoid duplicates) and an optional focus area, Claude proposes courses that are
in demand across the IT industry right now, each with a short rationale so the
admin can judge relevance to their org.

Like the rest of the AI layer this degrades gracefully -with no API key a
curated, hand-maintained list of evergreen-but-current IT topics is returned so
the feature stays demonstrable offline. Each suggestion's ``title`` feeds the
existing ``course_generator`` when the admin clicks "Add to catalogue".
"""
from __future__ import annotations

from app.ai import claude_client
from app.ai.claude_client import ClaudeError
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

MAX_COUNT = 12
MIN_COUNT = 1

_LEVELS = {"beginner", "intermediate", "advanced"}

_SYSTEM = (
    "You are a technology learning-and-development advisor who tracks skills "
    "demand across the software / IT industry. You recommend training that is "
    "genuinely trending and beneficial for IT organisations to upskill their "
    "staff. You are concrete and honest: you never invent vendors or "
    "certifications that do not exist, and your rationales reflect real hiring "
    "and adoption trends."
)


def _prompt(focus: str, count: int, exclude: list[str]) -> str:
    focus_line = (
        f"Focus the recommendations on this area: {focus}.\n"
        if focus
        else "Cover a broad, complementary mix across the IT industry.\n"
    )
    exclude_line = (
        "The organisation ALREADY offers these courses -do NOT repeat them or "
        "propose near-duplicates:\n" + "\n".join(f"- {t}" for t in exclude) + "\n"
        if exclude
        else ""
    )
    return f"""Recommend {count} training courses that are trending and beneficial \
for an IT-industry organisation to offer its employees right now.

{focus_line}{exclude_line}
For each course provide:
- a concise, specific course title (max ~80 chars)
- a 1-2 sentence description of what it covers
- a short category label (e.g. "Cloud", "Security", "AI/ML", "DevOps", "Data")
- a difficulty level: one of "beginner", "intermediate", "advanced"
- "why": one sentence on why it's in demand / beneficial to the org right now
- 3-5 key skills the learner gains

Return ONLY a JSON array (no prose, no markdown fences) of objects shaped like:
[
  {{
    "title": "...",
    "description": "...",
    "category": "...",
    "level": "intermediate",
    "why": "...",
    "skills": ["...", "..."]
  }}
]
"""


def _clean(item: dict) -> dict | None:
    title = (item.get("title") or "").strip()
    if not title:
        return None
    level = (item.get("level") or "").strip().lower()
    if level not in _LEVELS:
        level = "intermediate"
    skills = item.get("skills") or []
    if not isinstance(skills, list):
        skills = []
    return {
        "title": title[:120],
        "description": (item.get("description") or "").strip()[:400] or None,
        "category": (item.get("category") or "").strip()[:120] or None,
        "level": level,
        "why": (item.get("why") or "").strip()[:300] or None,
        "skills": [str(s).strip()[:60] for s in skills if str(s).strip()][:6],
    }


def _generate_with_claude(focus: str, count: int, exclude: list[str]) -> list[dict]:
    # Use the fast model with a bounded token budget: the output is a short JSON
    # array, so this keeps the admin page responsive (vs. the heavy default model).
    data = claude_client.complete_json(
        _SYSTEM,
        _prompt(focus, count, exclude),
        model=settings.CLAUDE_TRENDING_MODEL,
        max_tokens=3000,
    )
    if not isinstance(data, list):
        raise ClaudeError("Model did not return a JSON array of courses")
    cleaned = [c for c in (_clean(i) for i in data if isinstance(i, dict)) if c]
    if not cleaned:
        raise ClaudeError("Model returned no usable recommendations")
    return cleaned


# --------------------------------------------------------------------------- #
# Offline fallback -a curated list of currently-relevant IT topics
# --------------------------------------------------------------------------- #
_FALLBACK: list[dict] = [
    {
        "title": "Practical Generative AI & LLMs for Software Teams",
        "description": "How to build with large language models: prompting, RAG, and integrating AI into applications responsibly.",
        "category": "AI/ML",
        "level": "intermediate",
        "why": "GenAI is the fastest-growing skill demand across engineering orgs.",
        "skills": ["Prompt engineering", "RAG", "LLM APIs", "AI safety"],
    },
    {
        "title": "Cloud Fundamentals on AWS, Azure & GCP",
        "description": "Core cloud concepts across the three major providers: compute, storage, networking and cost.",
        "category": "Cloud",
        "level": "beginner",
        "why": "Cloud literacy is now baseline for nearly every IT role.",
        "skills": ["IaaS/PaaS", "Cloud networking", "Cost optimisation"],
    },
    {
        "title": "Kubernetes & Container Orchestration in Production",
        "description": "Deploying, scaling and operating containerised workloads with Kubernetes.",
        "category": "DevOps",
        "level": "advanced",
        "why": "Containers and K8s are the default for modern deployment.",
        "skills": ["Docker", "Kubernetes", "Helm", "Observability"],
    },
    {
        "title": "Cybersecurity Essentials & Secure Coding",
        "description": "Threat modelling, the OWASP Top 10, and writing code that resists common attacks.",
        "category": "Security",
        "level": "intermediate",
        "why": "Rising breach costs make security everyone's responsibility.",
        "skills": ["OWASP Top 10", "Threat modelling", "Secure SDLC"],
    },
    {
        "title": "CI/CD & DevOps Automation",
        "description": "Building reliable pipelines, infrastructure as code and automated delivery.",
        "category": "DevOps",
        "level": "intermediate",
        "why": "Faster, safer releases are a top priority for engineering orgs.",
        "skills": ["CI/CD", "IaC (Terraform)", "GitOps", "Automation"],
    },
    {
        "title": "Data Engineering & Modern Data Pipelines",
        "description": "Designing scalable pipelines, warehouses and ELT for analytics and ML.",
        "category": "Data",
        "level": "intermediate",
        "why": "Data infrastructure underpins analytics and AI initiatives.",
        "skills": ["SQL", "ETL/ELT", "Data warehousing", "Orchestration"],
    },
    {
        "title": "Site Reliability Engineering (SRE) Practices",
        "description": "SLOs, error budgets, incident response and building resilient systems.",
        "category": "DevOps",
        "level": "advanced",
        "why": "Reliability engineering keeps growing services dependable at scale.",
        "skills": ["SLIs/SLOs", "Incident response", "Observability"],
    },
    {
        "title": "AI-Assisted Software Development",
        "description": "Using AI coding assistants effectively and safely in day-to-day development.",
        "category": "AI/ML",
        "level": "beginner",
        "why": "AI pair-programming is rapidly changing developer productivity.",
        "skills": ["AI code assistants", "Code review", "Productivity"],
    },
    {
        "title": "Data Privacy & Compliance for Tech Teams",
        "description": "GDPR, data handling and privacy-by-design for engineers and product teams.",
        "category": "Security",
        "level": "beginner",
        "why": "Tightening global regulation makes privacy skills essential.",
        "skills": ["GDPR", "Privacy by design", "Data governance"],
    },
    {
        "title": "System Design & Scalable Architecture",
        "description": "Designing distributed systems -caching, queues, sharding and trade-offs.",
        "category": "Engineering",
        "level": "advanced",
        "why": "Architecture skills are a key differentiator for senior engineers.",
        "skills": ["Distributed systems", "Scalability", "Caching", "Trade-offs"],
    },
    {
        "title": "Platform Engineering & Internal Developer Platforms",
        "description": "Building self-service platforms that improve developer experience and velocity.",
        "category": "DevOps",
        "level": "advanced",
        "why": "Platform engineering is a leading trend for scaling productivity.",
        "skills": ["IDPs", "Developer experience", "Golden paths"],
    },
    {
        "title": "TypeScript & Modern Frontend Foundations",
        "description": "Type-safe JavaScript and the fundamentals behind modern web frameworks.",
        "category": "Engineering",
        "level": "beginner",
        "why": "TypeScript is now the default for maintainable web codebases.",
        "skills": ["TypeScript", "Tooling", "Component design"],
    },
]


def _generate_fallback(focus: str, count: int, exclude: list[str]) -> list[dict]:
    excluded = {t.strip().lower() for t in exclude}
    focus_l = (focus or "").strip().lower()
    items = [c for c in _FALLBACK if c["title"].lower() not in excluded]
    if focus_l:
        # Loosely prioritise items whose text mentions the focus area.
        def score(c: dict) -> int:
            blob = f"{c['title']} {c['category']} {c.get('description','')}".lower()
            return 0 if focus_l in blob else 1

        items = sorted(items, key=score)
    return [dict(c) for c in items[:count]]


def recommend(
    focus: str = "", count: int = 6, exclude: list[str] | None = None
) -> tuple[list[dict], str]:
    """Return ``(courses, source)`` where source is ``"ai"`` or ``"fallback"``."""
    focus = (focus or "").strip()
    count = max(MIN_COUNT, min(int(count or 6), MAX_COUNT))
    exclude = [t for t in (exclude or []) if t][:100]

    if claude_client.is_configured():
        try:
            return _generate_with_claude(focus, count, exclude)[:count], "ai"
        except ClaudeError as exc:
            logger.warning("Claude trending recommendation failed (%s); using fallback", exc)

    return _generate_fallback(focus, count, exclude), "fallback"
