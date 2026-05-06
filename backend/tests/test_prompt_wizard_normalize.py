"""Unit tests for _normalize_use_case in prompt_wizard_service.

Skipped automatically in the core CI where the premium package is not
available — runs in the full Docker stack and premium CI.
"""

from __future__ import annotations

import logging

import pytest

premium_wizard = pytest.importorskip(
    "premium.services.prompt_wizard_service",
    reason="premium package not available in core CI",
)
VALID_USE_CASES = premium_wizard.VALID_USE_CASES
_normalize_use_case = premium_wizard._normalize_use_case


# ---------------------------------------------------------------------------
# Fast-path: already-valid values pass through unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", sorted(VALID_USE_CASES))
def test_normalize_returns_valid_values_unchanged(value: str) -> None:
    assert _normalize_use_case(value) == value


# ---------------------------------------------------------------------------
# Mapping branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("multiple_choice", "question_generation_multiple_choice"),
        ("Multiple Choice", "question_generation_multiple_choice"),
        ("single_choice", "question_generation_multiple_choice"),
        (
            "question_generation_multiple_choice_advanced",
            "question_generation_multiple_choice",
        ),
        ("true_false", "question_generation_true_false"),
        ("True/False", "question_generation_true_false"),
        ("wahr_falsch", "question_generation_true_false"),
        ("Wahr/Falsch-Fragen", "question_generation_true_false"),
        ("open_ended", "question_generation_open_ended"),
        ("open ended question", "question_generation_open_ended"),
        ("code_completion", "question_generation_open_ended"),
        ("Code-Vervollständigung", "question_generation_open_ended"),
        ("fill_in_the_blank", "question_generation_open_ended"),
        ("short_answer", "question_generation_open_ended"),
        ("offen", "question_generation_open_ended"),
        ("evaluation_task", "evaluation"),
        ("Bewertungsaufgabe", "evaluation"),
        ("Korrektur", "evaluation"),
        ("chatbot_response", "chatbot"),
        ("dialog", "chatbot"),
    ],
)
def test_normalize_maps_to_expected_use_case(raw: str, expected: str) -> None:
    assert _normalize_use_case(raw) == expected


# ---------------------------------------------------------------------------
# Default fallback for unrecognized values
# ---------------------------------------------------------------------------


def test_normalize_falls_back_to_question_generation_for_unknown(caplog) -> None:
    with caplog.at_level(
        logging.WARNING, logger="premium.services.prompt_wizard_service"
    ):
        result = _normalize_use_case("completely_unknown_type_xyz")

    assert result == "question_generation"
    assert "unrecognized use_case" in caplog.text
    assert "completely_unknown_type_xyz" in caplog.text


def test_normalize_falls_back_for_empty_string(caplog) -> None:
    with caplog.at_level(
        logging.WARNING, logger="premium.services.prompt_wizard_service"
    ):
        result = _normalize_use_case("")

    assert result == "question_generation"
