"""Tests for structured_to_markdown.

The inputs mirror the shapes the model returned for structured open-ended
answers: a model answer object and a scoring rubric, as objects or as compact
JSON strings inside a text field.
"""

import json

import pytest

from services.structured_text import structured_to_markdown

MODEL_ANSWER = {
    "structure": "Empfohlene Struktur: (1) Ausgangslage, (2) SWOT",
    "key_points": ["Ausgangslage beschreiben", "SWOT-Matrix"],
    "model_answer": "1. Ausgangslage:\nZiele festhalten.\n\n2. SWOT:\nStärken: Team.",
}

RUBRIC = {
    "total_points": 20,
    "criteria": [
        {"aspect": "Analyse", "points": 5, "description": "Vollständig"},
        {"aspect": "SWOT", "points": 5, "description": "Mit Massnahmen"},
    ],
}


def test_model_answer_dict_becomes_markdown():
    """A heading the model repeats inside the value appears only once."""
    assert structured_to_markdown(MODEL_ANSWER) == (
        "**Empfohlene Struktur:**\n\n(1) Ausgangslage, (2) SWOT"
        "\n\n**Kernpunkte:**\n\n- Ausgangslage beschreiben\n- SWOT-Matrix"
        "\n\n**Musterantwort:**\n\n1. Ausgangslage:\nZiele festhalten.\n\n"
        "2. SWOT:\nStärken: Team."
    )


def test_compact_json_string_is_parsed_and_rendered():
    """The model writes the object as a compact JSON string into the text
    field; ``\\n`` there are JSON escapes, not line breaks."""
    raw = json.dumps(MODEL_ANSWER, ensure_ascii=False, separators=(",", ":"))
    rendered = structured_to_markdown(raw)
    assert rendered == structured_to_markdown(MODEL_ANSWER)
    assert "\\n" not in rendered
    assert "Ziele festhalten.\n\n2. SWOT" in rendered


def test_rubric_renders_points_per_criterion():
    assert structured_to_markdown(json.dumps(RUBRIC)) == (
        "**Gesamtpunkte: 20**\n\n**Bewertungskriterien:**\n\n"
        "- **Analyse** (5 Punkte): Vollständig\n"
        "- **SWOT** (5 Punkte): Mit Massnahmen"
    )


def test_fenced_json_string_is_rendered():
    raw = "```json\n" + json.dumps(RUBRIC) + "\n```"
    assert structured_to_markdown(raw) == structured_to_markdown(RUBRIC)


def test_criterion_extra_keys_are_kept():
    """Keys beyond name/points/description must not be dropped silently."""
    rubric = [
        {
            "criterion": "Analyse",
            "max_points": 4,
            "description": "Tiefe",
            "indicators": ["Ursachen", "Folgen"],
        }
    ]
    assert structured_to_markdown(rubric) == (
        "- **Analyse** (4 Punkte): Tiefe (Indicators: Ursachen; Folgen)"
    )


def test_key_point_dict_keeps_all_fields():
    value = {"key_points": [{"name": "Kohäsion", "explanation": "eng", "example": "X"}]}
    assert structured_to_markdown(value) == (
        "**Kernpunkte:**\n\n- **Kohäsion** (Explanation: eng; Example: X)"
    )


def test_rubric_keyed_by_criterion_renders_one_line_each():
    value = {
        "criteria": {
            "content_accuracy": {"description": "Sachlich richtig", "max_points": 5},
            "completeness": {"description": "Vollständig", "max_points": 3},
        },
        "overview": "Beschreibt das Modell.",
    }
    assert structured_to_markdown(value) == (
        "**Bewertungskriterien:**\n\n"
        "- **Content accuracy** (5 Punkte): Sachlich richtig\n"
        "- **Completeness** (3 Punkte): Vollständig"
        "\n\n**Overview:**\n\nBeschreibt das Modell."
    )


def test_nested_points_are_not_python_repr():
    rendered = structured_to_markdown([{"aspect": "A", "points": {"min": 1, "max": 3}}])
    assert "{" not in rendered
    assert rendered == "- **A** (Min: 1; Max: 3 Punkte)"


def test_list_becomes_bullets():
    assert structured_to_markdown(["A", "B"]) == "- A\n- B"


def test_unknown_keys_keep_their_content():
    rendered = structured_to_markdown({"grading_hint": "Teilpunkte möglich"})
    assert rendered == "**Grading hint:**\n\nTeilpunkte möglich"


def test_non_string_keys_do_not_crash():
    assert structured_to_markdown({1: "x"}) == "**1:**\n\nx"


def test_empty_nested_values_are_skipped():
    assert structured_to_markdown({"a": {}, "b": "x", "c": [None]}) == "**B:**\n\nx"


@pytest.mark.parametrize("value", [{}, [], [None], {"structure": "", "key_points": []}])
def test_object_that_renders_empty_becomes_none(value):
    """Never turn an object into an empty-string answer."""
    assert structured_to_markdown(value) is None


@pytest.mark.parametrize(
    "text",
    [
        '{"name": "Max", "age": 30}',  # answer to "write a JSON object"
        "[1, 2, 3]",
        '["Siehe Folie 3"]',
        "{}",
        "[]",
        '{"structure": ""}',  # structured, but renders empty
    ],
)
def test_json_that_is_not_a_model_answer_is_unchanged(text):
    assert structured_to_markdown(text) is text


def test_plain_text_is_unchanged():
    text = "Struktur: Analyse → Massnahmen\n\nKey Points:\n1. Vollständig"
    assert structured_to_markdown(text) is text


def test_text_starting_with_brace_but_invalid_json_is_unchanged():
    text = "{Vorbemerkung} Die Antwort beginnt mit einer Klammer."
    assert structured_to_markdown(text) is text


def test_json_followed_by_text_is_unchanged():
    text = '{"total_points": 5} Zusatztext'
    assert structured_to_markdown(text) is text


@pytest.mark.parametrize("text", ['"nur ein String"', "true", "123", "null"])
def test_json_scalar_string_is_unchanged(text):
    assert structured_to_markdown(text) is text


def test_none_is_unchanged():
    assert structured_to_markdown(None) is None


@pytest.mark.parametrize(
    "value",
    [
        MODEL_ANSWER,
        RUBRIC,
        json.dumps(RUBRIC),
        [{"aspect": "A", "points": 2}],
        {"criteria": {"accuracy": {"description": "d", "max_points": 1}}},
    ],
)
def test_rendering_is_idempotent(value):
    """The data-fix script relies on a second run changing nothing."""
    once = structured_to_markdown(value)
    assert structured_to_markdown(once) == once
