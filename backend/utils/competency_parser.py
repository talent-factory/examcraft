"""Parser: derives structured competencies from rendered_text (TF-400).

The ``rendered_text`` of a CompetencyFramework is the complete HKP text
(BWZ format). The individual competencies (HK) are extracted from it, so
structured tagging (competency_code → competency_id) has a data basis —
without having to capture the HKs by hand separately.

Expected source format (Markdown):

    ### B1 <title of the competency>

    - <performance criterion> (LN 2)
    - <another criterion> (LN 1)

    ### B2 <title>
    ...

Only ``###`` headings with a code pattern (letter + digits, e.g.
``B1``, ``A6``) count as an HK. Codes must exactly match those the model
returns as ``competency_code`` (key consistency, cf. TF-384) — both come
from the same rendered_text.
"""

import re
from typing import TypedDict

# ### B1 Title  → code (letter + digits), title
_HEADING = re.compile(r"^###\s+([A-Za-z]\d+)\s+(.+?)\s*$")
# - Criterion (LN 2)  → text, LN level
_BULLET_WITH_LN = re.compile(r"^\s*[-*]\s+(.*?)\s*\(LN\s*(\d+)\)\s*$")
# - Criterion without an LN value
_BULLET = re.compile(r"^\s*[-*]\s+(.+?)\s*$")

# Valid LN level range (matches DescriptorIn ge=1/le=4 and
# QuestionReview.ln_level). rendered_text is free text — levels outside
# this range are invalid and are discarded.
_LN_MIN, _LN_MAX = 1, 4


class ParsedDescriptor(TypedDict):
    """A performance criterion of an HK; ``ln_level`` is 1-4 or None."""

    text: str
    ln_level: int | None


class ParsedCompetency(TypedDict):
    """A competency derived from rendered_text."""

    code: str
    title: str
    descriptors: list[ParsedDescriptor]
    position: int


def _coerce_ln_level(raw: str) -> int | None:
    """LN level from the source text: only 1-4 valid, otherwise None.

    Prevents a level made up in the rendered_text (``(LN 9)``,
    ``(LN 0)``) from ending up unchecked in the descriptors JSON and
    thus in tagging.
    """
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if _LN_MIN <= value <= _LN_MAX else None


def parse_competencies(rendered_text: str | None) -> list[ParsedCompetency]:
    """Parses rendered_text into a list of HK dicts (``ParsedCompetency``).

    Returns per HK: ``{"code", "title", "descriptors": [{"text", "ln_level"}],
    "position"}`` in order of appearance. Empty/unstructured text
    yields ``[]``. Invalid LN levels are reduced to None.
    """
    competencies: list[ParsedCompetency] = []
    current: ParsedCompetency | None = None

    for line in (rendered_text or "").splitlines():
        heading = _HEADING.match(line)
        if heading:
            current = {
                "code": heading.group(1),
                "title": heading.group(2).strip(),
                "descriptors": [],
                "position": len(competencies),
            }
            competencies.append(current)
            continue

        # Ignore bullets outside an HK heading (e.g. in the description
        # of the competency area).
        if current is None:
            continue

        with_ln = _BULLET_WITH_LN.match(line)
        if with_ln:
            current["descriptors"].append(
                {
                    "text": with_ln.group(1).strip(),
                    "ln_level": _coerce_ln_level(with_ln.group(2)),
                }
            )
            continue

        bullet = _BULLET.match(line)
        if bullet:
            current["descriptors"].append(
                {"text": bullet.group(1).strip(), "ln_level": None}
            )

    return competencies
