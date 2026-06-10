"""Tests für den Competency-Parser (TF-400 Phase 2).

Der Parser leitet strukturierte Handlungskompetenzen (B1/B2/...) aus dem
``rendered_text`` eines CompetencyFramework ab — dieselbe Quelle, die via
``{{ competencies }}`` in den Prompt fliesst (kein Doppel-Erfassen).
"""

from utils.competency_parser import parse_competencies

MODUL_B = """# Handlungskompetenzen (HKB) - Wirkungsvoll kommunizieren

## Beschreibung des Handlungskompetenzbereiches

Irgendein Beschreibungstext.

## Handlungskompetenz

### B1 Intern und extern sachlogisch kommunizieren

- Sie setzen einfache Kommunikationsmodelle ein. (LN 2)
- Sie formen Fachbegriffe in verständliche Sprache um. (LN 1)

### B2 Die eigene Meinung vertreten

- Sie vertreten eine Sachlage mit Argumenten. (LN 3)

### B3 Kunden beraten und verkaufswirksame Lösungen präsentieren

- Sie treten verkaufswirksam auf. (LN 3)
"""

# Nicht-fortlaufende Codes (wie BWZ Modul A: A1, A2, A6).
MODUL_A = """## Handlungskompetenz

### A1 Regeln vereinbaren

- Sie vereinbaren Regeln. (LN 2)

### A6 Gesetzliche Bestimmungen einhalten

- Ein Kriterium ohne Stufe.
- Sie halten Bestimmungen ein. (LN 4)
"""


def test_parses_codes_titles_in_order():
    result = parse_competencies(MODUL_B)
    assert [c["code"] for c in result] == ["B1", "B2", "B3"]
    assert result[0]["title"] == "Intern und extern sachlogisch kommunizieren"
    assert result[2]["title"] == (
        "Kunden beraten und verkaufswirksame Lösungen präsentieren"
    )
    # position spiegelt die Reihenfolge
    assert [c["position"] for c in result] == [0, 1, 2]


def test_parses_descriptors_with_ln_level():
    result = parse_competencies(MODUL_B)
    b1 = result[0]
    assert b1["descriptors"] == [
        {"text": "Sie setzen einfache Kommunikationsmodelle ein.", "ln_level": 2},
        {"text": "Sie formen Fachbegriffe in verständliche Sprache um.", "ln_level": 1},
    ]


def test_handles_non_contiguous_codes_and_missing_ln():
    result = parse_competencies(MODUL_A)
    assert [c["code"] for c in result] == ["A1", "A6"]
    a6 = result[1]
    # Bullet ohne (LN n) → ln_level None, voller Text erhalten
    assert a6["descriptors"][0] == {
        "text": "Ein Kriterium ohne Stufe.",
        "ln_level": None,
    }
    assert a6["descriptors"][1]["ln_level"] == 4


def test_empty_or_unstructured_text_yields_no_competencies():
    assert parse_competencies("") == []
    assert parse_competencies("Nur Fliesstext ohne HK-Überschriften.") == []
    # ## (h2) ist kein HK-Heading — nur ### mit Code-Muster zählt
    assert parse_competencies("## B1 Kein echtes HK-Heading") == []


def test_out_of_range_ln_level_is_dropped_to_none():
    """LN-Stufen ausserhalb 1–4 sind ungültig (vgl. DescriptorIn ge=1, le=4 und
    QuestionReview.ln_level) und werden auf None reduziert — der Kriteriumstext
    bleibt erhalten. Sonst gelangt eine vom Quelltext erfundene Stufe (z. B.
    ``(LN 9)``) ungeprüft ins descriptors-JSON.
    """
    text = (
        "## Handlungskompetenz\n\n"
        "### C1 Test\n\n"
        "- Stufe zu hoch. (LN 9)\n"
        "- Stufe null. (LN 0)\n"
        "- Gültige Stufe. (LN 3)\n"
    )
    descriptors = parse_competencies(text)[0]["descriptors"]
    assert descriptors[0] == {"text": "Stufe zu hoch.", "ln_level": None}
    assert descriptors[1] == {"text": "Stufe null.", "ln_level": None}
    assert descriptors[2] == {"text": "Gültige Stufe.", "ln_level": 3}
