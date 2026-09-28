"""EU AI Act Art. 50 disclosure for exports (TF-747).

Single source of truth for the machine-readable and visible AI marking that
every exam/grade export carries. Exams are assembled from AI-generated task
drafts and grades come from AI-assisted grading suggestions, so the marking is
applied at export level (there is no per-question provenance flag).

Visible texts live in the locale files (``export_ai_notice``,
``export_ai_notice_grades``); the machine-readable fields below are
language-independent so downstream tools can rely on them.
"""

from __future__ import annotations

from services.translation_service import DEFAULT_LOCALE, t

GENERATOR = "ExamCraft AI"
REGULATION = "EU AI Act (Regulation (EU) 2024/1689), Art. 50"

# Machine-readable marker: JSON exports embed it verbatim, PDF/XML exports map
# it onto document metadata / tags.
AI_DISCLOSURE: dict[str, object] = {
    "ai_generated_content": True,
    "generator": GENERATOR,
    "regulation": REGULATION,
    "human_review": "responsible teacher finalises and approves",
}

# Short token for XML tags / PDF keywords / HTTP header value.
AI_DISCLOSURE_TAG = "ai-generated"

# Response header on all exam/grade export downloads.
AI_DISCLOSURE_HEADER = "X-AI-Generated-Content"


def exam_ai_notice(locale: str = DEFAULT_LOCALE) -> str:
    """Visible notice for exam exports (AI-generated task drafts)."""
    return t("export_ai_notice", locale=locale)


def grades_ai_notice(locale: str = DEFAULT_LOCALE) -> str:
    """Visible notice for grade exports (AI-assisted grading suggestions)."""
    return t("export_ai_notice_grades", locale=locale)
