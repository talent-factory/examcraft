"""Parser: leitet strukturierte Handlungskompetenzen aus rendered_text ab (TF-400).

Der ``rendered_text`` eines CompetencyFramework ist der vollständige HKP-Text
(BWZ-Format). Daraus werden die einzelnen Handlungskompetenzen (HK) gewonnen,
damit das strukturierte Tagging (competency_code → competency_id) eine
Datengrundlage hat — ohne die HKs zusätzlich von Hand erfassen zu müssen.

Erwartetes Quellformat (Markdown):

    ### B1 <Titel der Handlungskompetenz>

    - <Leistungskriterium> (LN 2)
    - <weiteres Kriterium> (LN 1)

    ### B2 <Titel>
    ...

Nur ``###``-Überschriften mit einem Code-Muster (Buchstabe + Ziffern, z. B.
``B1``, ``A6``) zählen als HK. Codes müssen exakt jenen entsprechen, die das
Modell als ``competency_code`` zurückgibt (Key-Konsistenz, vgl. TF-384) — beide
stammen aus demselben rendered_text.
"""

import re
from typing import TypedDict

# ### B1 Titel  → Code (Buchstabe + Ziffern), Titel
_HEADING = re.compile(r"^###\s+([A-Za-z]\d+)\s+(.+?)\s*$")
# - Kriterium (LN 2)  → Text, LN-Stufe
_BULLET_WITH_LN = re.compile(r"^\s*[-*]\s+(.*?)\s*\(LN\s*(\d+)\)\s*$")
# - Kriterium ohne LN-Angabe
_BULLET = re.compile(r"^\s*[-*]\s+(.+?)\s*$")

# Gültiger LN-Stufen-Bereich (deckungsgleich mit DescriptorIn ge=1/le=4 und
# QuestionReview.ln_level). rendered_text ist freier Text — Stufen ausserhalb
# dieses Bereichs sind ungültig und werden verworfen.
_LN_MIN, _LN_MAX = 1, 4


class ParsedDescriptor(TypedDict):
    """Ein Leistungskriterium einer HK; ``ln_level`` ist 1–4 oder None."""

    text: str
    ln_level: int | None


class ParsedCompetency(TypedDict):
    """Eine aus rendered_text abgeleitete Handlungskompetenz."""

    code: str
    title: str
    descriptors: list[ParsedDescriptor]
    position: int


def _coerce_ln_level(raw: str) -> int | None:
    """LN-Stufe aus dem Quelltext: nur 1–4 gültig, sonst None.

    Verhindert, dass eine im rendered_text erfundene Stufe (``(LN 9)``,
    ``(LN 0)``) ungeprüft ins descriptors-JSON und damit ins Tagging gelangt.
    """
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if _LN_MIN <= value <= _LN_MAX else None


def parse_competencies(rendered_text: str | None) -> list[ParsedCompetency]:
    """Parst rendered_text in eine Liste von HK-Dicts (``ParsedCompetency``).

    Rückgabe je HK: ``{"code", "title", "descriptors": [{"text", "ln_level"}],
    "position"}`` in Reihenfolge des Auftretens. Leerer/unstrukturierter Text
    ergibt ``[]``. Ungültige LN-Stufen werden auf None reduziert.
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

        # Bullets ausserhalb einer HK-Überschrift ignorieren (z. B. in der
        # Beschreibung des Handlungskompetenzbereiches).
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
