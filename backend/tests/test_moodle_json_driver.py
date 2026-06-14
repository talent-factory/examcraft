"""Tests for the Moodle JSON results import driver (TF-423).

The JSON export pairs each answer with its question text
(``frageN``/``antwortN``), so the driver maps answers to exam questions by
**content** (normalised text match), not by column position. This makes the
import robust against Moodle quiz reordering / A-B variants — the failure
mode the bare-CSV driver could only guard against, never resolve.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from services.import_drivers.base import ColumnMappingError, ImportDriverError
from services.import_drivers.moodle_json_driver import MoodleJsonDriver


def _question(
    eq_id: int, position: int, text: str, *, options=None, qtype="open_ended"
):
    """Build an ExamQuestion-like stub (``.id``, ``.position``, ``.question``)."""
    inner = SimpleNamespace(question_text=text, options=options, question_type=qtype)
    return SimpleNamespace(
        id=eq_id, position=position, external_refs=None, question=inner
    )


def _exam(questions):
    return SimpleNamespace(id=1, questions=list(questions))


def _source(students, *, wrap=True):
    """Serialise like the Moodle plugin export: ``[[ {student}, ... ]]``."""
    return json.dumps([students] if wrap else students)


def _parse(students, exam, *, wrap=True):
    return MoodleJsonDriver().parse(_source(students, wrap=wrap), exam=exam)


def test_driver_name_is_moodle_json():
    assert MoodleJsonDriver.name == "moodle_json"


def test_maps_answers_by_question_text_not_position():
    """Reorder-robustness: JSON column order differs from exam position order."""
    exam = _exam(
        [
            _question(
                101,
                1,
                "Was ist 2 plus 2?",
                options=["A) 3", "B) 4"],
                qtype="single_choice",
            ),
            _question(102, 2, "Beschreibe die Kommunikation im Projekt."),
        ]
    )
    # JSON order is REVERSED vs exam position: frage1=essay(Q102), frage2=MC(Q101)
    student = {
        "nachname": "Meyer",
        "vorname": "Jennifer",
        "e-mail-adresse": "j.meyer@example.ch",
        "begonnen": "12. Juni 2026 10:30",
        "beendet": "12. Juni 2026 11:55",
        "frage1": "Beschreibe die Kommunikation im Projekt.",
        "antwort1": "Die Kommunikation war unklar und fachlich zu komplex.",
        "frage2": "Was ist 2 plus 2?",
        "antwort2": "Option B: 4",
    }
    payload = _parse([student], exam)
    answers = {a.exam_question_id: a.given_answer for a in payload.attempts[0].answers}
    assert answers[102].startswith("Die Kommunikation")
    assert answers[101] == "Option B: 4"


def test_ambiguous_question_text_raises():
    exam = _exam([_question(1, 1, "Gleiche Frage"), _question(2, 2, "Gleiche Frage")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": "Gleiche Frage",
        "antwort1": "x",
    }
    with pytest.raises(ColumnMappingError):
        _parse([student], exam)


def test_unmatched_question_text_raises():
    exam = _exam([_question(1, 1, "Frage A über Schreinerei")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": "Voellig andere Frage XYZ ohne Bezug",
        "antwort1": "x",
    }
    with pytest.raises(ColumnMappingError):
        _parse([student], exam)


def test_matches_across_markdown_and_plain_forms():
    """ExamCraft stores Markdown; the JSON frage is Moodle-rendered plain text."""
    exam = _exam([_question(7, 1, "**Szenario:** Kommunikation in der Schreinerei")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": "Szenario: Kommunikation in der Schreinerei",
        "antwort1": "...",
    }
    payload = _parse([student], exam)
    assert payload.attempts[0].answers[0].exam_question_id == 7


def test_matches_across_html_entity_form():
    """Moodle question text can arrive HTML-entity-encoded."""
    exam = _exam([_question(8, 1, "Anpassung der Sprache an den Kunden")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": "&lt;p&gt;Anpassung der Sprache an den Kunden&lt;/p&gt;",
        "antwort1": "...",
    }
    payload = _parse([student], exam)
    assert payload.attempts[0].answers[0].exam_question_id == 8


def test_mc_stem_is_prefix_of_rendered_frage_with_options():
    """MC export renders the options inline after the stem; stem ⊂ frage."""
    exam = _exam(
        [
            _question(
                5,
                1,
                "Wie planst du deinen Arbeitstag?",
                options=["A) gar nicht", "B) feste Zeitbloecke"],
                qtype="single_choice",
            )
        ]
    )
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": "Wie planst du deinen Arbeitstag?   : Option A: gar nicht; Option B: feste Zeitbloecke",
        "antwort1": "Option B: feste Zeitbloecke",
    }
    payload = _parse([student], exam)
    assert payload.attempts[0].answers[0].exam_question_id == 5


def test_parses_student_and_attempt_fields():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {
        "nachname": "Meyer",
        "vorname": "Jennifer",
        "e-mail-adresse": "j.meyer@example.ch",
        "begonnen": "12. Juni 2026 10:30",
        "beendet": "12. Juni 2026 11:55",
        "frage1": "Frage A",
        "antwort1": "meine antwort",
    }
    payload = _parse([student], exam)
    assert payload.driver_name == "moodle_json"
    assert payload.exam_id == 1
    assert len(payload.students) == 1
    s = payload.students[0]
    assert s.external_id == "j.meyer@example.ch"
    assert "Jennifer" in s.display_name and "Meyer" in s.display_name
    a = payload.attempts[0]
    assert a.student_external_id == "j.meyer@example.ch"
    assert a.started_at is not None
    assert a.submitted_at is not None
    assert a.source_attempt_id  # deterministic, non-empty


def test_source_attempt_id_is_deterministic():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "begonnen": "12. Juni 2026 10:30",
        "frage1": "Frage A",
        "antwort1": "x",
    }
    first = _parse([student], exam).attempts[0].source_attempt_id
    second = _parse([student], exam).attempts[0].source_attempt_id
    assert first == second


def test_accepts_flat_list_without_outer_wrapper():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {"e-mail-adresse": "a@example.ch", "frage1": "Frage A", "antwort1": "x"}
    payload = _parse([student], exam, wrap=False)
    assert len(payload.attempts) == 1


def test_accepts_bytes_source():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {"e-mail-adresse": "a@example.ch", "frage1": "Frage A", "antwort1": "x"}
    payload = MoodleJsonDriver().parse(_source([student]).encode("utf-8"), exam=exam)
    assert payload.attempts[0].answers[0].exam_question_id == 1


def test_extracts_class_hint_from_klasse_key():
    """TF-336 class auto-assignment survives the JSON path via the ``klasse`` key."""
    exam = _exam([_question(1, 1, "Frage A")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "klasse": "INF-23a",
        "frage1": "Frage A",
        "antwort1": "x",
    }
    payload = _parse([student], exam)
    assert payload.students[0].class_hint == "INF-23a"


def test_extracts_class_hint_from_english_class_alias():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "class": "INF-23b",
        "frage1": "Frage A",
        "antwort1": "x",
    }
    payload = _parse([student], exam)
    assert payload.students[0].class_hint == "INF-23b"


def test_blank_class_hint_is_none():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "klasse": "   ",
        "frage1": "Frage A",
        "antwort1": "x",
    }
    payload = _parse([student], exam)
    assert payload.students[0].class_hint is None


def test_missing_class_hint_is_none():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {"e-mail-adresse": "a@example.ch", "frage1": "Frage A", "antwort1": "x"}
    payload = _parse([student], exam)
    assert payload.students[0].class_hint is None


def test_multiple_attempts_per_student_get_incrementing_numbers():
    """Two rows for one student → attempt_number 1, 2 (uq_attempts_submission_number).

    A hardcoded attempt_number would collide on the (submission_id,
    attempt_number) unique constraint when a student has >1 attempt.
    """
    exam = _exam([_question(1, 1, "Frage A")])
    students = [
        {
            "e-mail-adresse": "a@example.ch",
            "begonnen": "2026-05-15 09:00:00",
            "frage1": "Frage A",
            "antwort1": "x",
        },
        {
            "e-mail-adresse": "a@example.ch",
            "begonnen": "2026-05-16 10:00:00",
            "frage1": "Frage A",
            "antwort1": "y",
        },
        {
            "e-mail-adresse": "b@example.ch",
            "begonnen": "2026-05-15 09:00:00",
            "frage1": "Frage A",
            "antwort1": "z",
        },
    ]
    payload = _parse(students, exam)
    by_student: dict[str, list[int]] = {}
    for att in payload.attempts:
        by_student.setdefault(att.student_external_id, []).append(att.attempt_number)
    assert sorted(by_student["a@example.ch"]) == [1, 2]
    assert by_student["b@example.ch"] == [1]
    # source_attempt_id stays unique per attempt.
    ids = [a.source_attempt_id for a in payload.attempts]
    assert len(ids) == len(set(ids))


def test_empty_source_raises_leer():
    exam = _exam([_question(1, 1, "Frage A")])
    with pytest.raises(ImportDriverError, match="leer"):
        MoodleJsonDriver().parse(b"", exam=exam)


def test_missing_frage_keys_raise_column_mapping_error():
    """JSON rows without any frageN key cannot be mapped → hard failure."""
    exam = _exam([_question(1, 1, "Frage A")])
    students = [{"e-mail-adresse": "a@example.ch", "antwort1": "x"}]
    with pytest.raises(ColumnMappingError):
        _parse(students, exam)


def test_row_without_email_becomes_row_error():
    """Per-row tolerance: an identity-less row is skipped with an error."""
    exam = _exam([_question(1, 1, "Frage A")])
    students = [
        {"e-mail-adresse": "", "frage1": "Frage A", "antwort1": "x"},
        {"e-mail-adresse": "ok@example.ch", "frage1": "Frage A", "antwort1": "y"},
    ]
    payload = _parse(students, exam)
    assert len(payload.attempts) == 1
    assert payload.attempts[0].student_external_id == "ok@example.ch"
    assert len(payload.errors) == 1
    assert payload.errors[0].row_index == 0


def test_multiple_students_share_one_question_mapping():
    exam = _exam(
        [
            _question(101, 1, "Frage Eins"),
            _question(102, 2, "Frage Zwei"),
        ]
    )
    students = [
        {
            "e-mail-adresse": "a@example.ch",
            "frage1": "Frage Eins",
            "antwort1": "a1",
            "frage2": "Frage Zwei",
            "antwort2": "a2",
        },
        {
            "e-mail-adresse": "b@example.ch",
            "frage1": "Frage Eins",
            "antwort1": "b1",
            "frage2": "Frage Zwei",
            "antwort2": "b2",
        },
    ]
    payload = _parse(students, exam)
    assert len(payload.attempts) == 2
    for attempt in payload.attempts:
        mapped = {a.exam_question_id for a in attempt.answers}
        assert mapped == {101, 102}


# ---------------------------------------------------------------------------
# Per-row (A/B variant) mapping — each row mapped by ITS OWN frageN layout
# ---------------------------------------------------------------------------
def test_per_row_mapping_handles_ab_variants_with_swapped_columns():
    """Two students with the same questions in DIFFERENT columns each map
    by their own frageN — a variant's answers never land on another's
    questions. The single-map-from-row-0 approach would misgrade student B.
    """
    exam = _exam([_question(101, 1, "Frage Eins"), _question(102, 2, "Frage Zwei")])
    students = [
        {
            "e-mail-adresse": "a@example.ch",
            "frage1": "Frage Eins",
            "antwort1": "a-eins",
            "frage2": "Frage Zwei",
            "antwort2": "a-zwei",
        },
        {  # columns swapped relative to student A
            "e-mail-adresse": "b@example.ch",
            "frage1": "Frage Zwei",
            "antwort1": "b-zwei",
            "frage2": "Frage Eins",
            "antwort2": "b-eins",
        },
    ]
    payload = _parse(students, exam)
    by_student = {
        att.student_external_id: {
            a.exam_question_id: a.given_answer for a in att.answers
        }
        for att in payload.attempts
    }
    assert by_student["a@example.ch"] == {101: "a-eins", 102: "a-zwei"}
    # B's antwort1 belongs to "Frage Zwei" (102); antwort2 to "Frage Eins" (101).
    assert by_student["b@example.ch"] == {101: "b-eins", 102: "b-zwei"}


def test_divergent_unresolvable_row_diverts_to_errors_not_abort():
    """A later row whose layout can't be resolved is a per-row error; the
    reference row (and other valid rows) still import.
    """
    exam = _exam([_question(1, 1, "Frage A über Schreinerei")])
    students = [
        {
            "e-mail-adresse": "ok@example.ch",
            "frage1": "Frage A über Schreinerei",
            "antwort1": "x",
        },
        {
            "e-mail-adresse": "bad@example.ch",
            "frage1": "Voellig andere Frage XYZ",
            "antwort1": "y",
        },
    ]
    payload = _parse(students, exam)
    assert len(payload.attempts) == 1
    assert payload.attempts[0].student_external_id == "ok@example.ch"
    assert len(payload.errors) == 1
    assert payload.errors[0].row_index == 1


# ---------------------------------------------------------------------------
# Jaccard fuzzy-match tier (the only tier that can pick a wrong-but-plausible
# question) — resolve, below-threshold abort, and near-tie abort.
# ---------------------------------------------------------------------------
# 13 tokens so a single-token difference scores 12/14 = 0.857 ≥ 0.85, and the
# differing token sits in the MIDDLE so neither string contains the other
# (forcing the match past the exact + containment tiers into Jaccard).
_Q13 = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu"
_FRAGE_ONE_DIFF = "alpha beta gamma delta epsilon zeta xi theta iota kappa lambda mu nu"
_FRAGE_TWO_DIFF = (
    "alpha beta gamma delta epsilon zeta xi theta iota kappa lambda mu omikron"
)


def test_jaccard_tier_resolves_single_near_match():
    exam = _exam([_question(42, 1, _Q13)])
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": _FRAGE_ONE_DIFF,
        "antwort1": "x",
    }
    payload = _parse([student], exam)
    assert payload.attempts[0].answers[0].exam_question_id == 42


def test_jaccard_below_threshold_aborts():
    exam = _exam([_question(42, 1, _Q13)])  # two differing tokens → 11/15 ≈ 0.73
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": _FRAGE_TWO_DIFF,
        "antwort1": "x",
    }
    with pytest.raises(ColumnMappingError):
        _parse([student], exam)


def test_jaccard_near_tie_aborts():
    """Two questions with identical token sets score equally above threshold
    → ambiguous tie → abort (never grade against an arbitrary one)."""
    q_reversed = " ".join(reversed(_Q13.split()))
    exam = _exam([_question(1, 1, _Q13), _question(2, 2, q_reversed)])
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": _FRAGE_ONE_DIFF,
        "antwort1": "x",
    }
    with pytest.raises(ColumnMappingError):
        _parse([student], exam)


def test_duplicate_eq_id_target_aborts():
    """Two distinct frageN columns resolving to the SAME exam question →
    abort (the `duplicates` guardrail, distinct from the ambiguous-text one)."""
    exam = _exam([_question(7, 1, "Beschreibe die Kommunikation im Projekt")])
    student = {
        "e-mail-adresse": "a@example.ch",
        # Both frage texts contain the stored stem → both resolve to eq 7.
        "frage1": "Beschreibe die Kommunikation im Projekt ausführlich",
        "antwort1": "x",
        "frage2": "Beschreibe die Kommunikation im Projekt kurz",
        "antwort2": "y",
    }
    with pytest.raises(ColumnMappingError):
        _parse([student], exam)


# ---------------------------------------------------------------------------
# Date parsing — value-level assertions + tz-awareness (the idempotency key
# embeds isoformat(), so a naïve/aware drift silently changes keys).
# ---------------------------------------------------------------------------
def test_naive_date_is_parsed_as_utc():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "begonnen": "2026-05-15 09:00:00",
        "frage1": "Frage A",
        "antwort1": "x",
    }
    started = _parse([student], exam).attempts[0].started_at
    assert started == datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)
    assert started.tzinfo == timezone.utc


def test_tz_aware_date_is_converted_to_utc():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "begonnen": "2026-06-12T10:30:00+02:00",  # → 08:30 UTC
        "frage1": "Frage A",
        "antwort1": "x",
    }
    started = _parse([student], exam).attempts[0].started_at
    assert started == datetime(2026, 6, 12, 8, 30, tzinfo=timezone.utc)


def test_german_long_date_parses_to_correct_value():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {
        "e-mail-adresse": "a@example.ch",
        "begonnen": "12. Juni 2026 10:30",
        "frage1": "Frage A",
        "antwort1": "x",
    }
    started = _parse([student], exam).attempts[0].started_at
    assert started == datetime(2026, 6, 12, 10, 30, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# _load_rows error / tolerance branches
# ---------------------------------------------------------------------------
def test_invalid_json_raises():
    exam = _exam([_question(1, 1, "Frage A")])
    with pytest.raises(ImportDriverError, match="gültiges JSON"):
        MoodleJsonDriver().parse("{ not json", exam=exam)


def test_non_list_root_raises():
    exam = _exam([_question(1, 1, "Frage A")])
    with pytest.raises(ImportDriverError, match="Liste"):
        MoodleJsonDriver().parse(json.dumps({"nachname": "x"}), exam=exam)


def test_non_utf8_bytes_raise():
    exam = _exam([_question(1, 1, "Frage A")])
    with pytest.raises(ImportDriverError, match="UTF-8"):
        MoodleJsonDriver().parse(b"\xff\xff\xff", exam=exam)


def test_non_dict_rows_are_skipped_with_a_warning():
    exam = _exam([_question(1, 1, "Frage A")])
    source = json.dumps(
        [
            [
                {
                    "e-mail-adresse": "a@example.ch",
                    "frage1": "Frage A",
                    "antwort1": "x",
                },
                None,
                7,
            ]
        ]
    )
    payload = MoodleJsonDriver().parse(source, exam=exam)
    assert len(payload.attempts) == 1
    assert any("Objektstruktur" in w for w in payload.warnings)


def test_empty_exam_raises():
    with pytest.raises(ImportDriverError, match="keine Fragen"):
        _parse(
            [{"e-mail-adresse": "a@example.ch", "frage1": "Frage A", "antwort1": "x"}],
            _exam([]),
        )


# ---------------------------------------------------------------------------
# Secondary sanity-net warning — surfaced, aggregated, non-fatal
# ---------------------------------------------------------------------------
def test_choice_answer_matching_no_option_warns_once_aggregated():
    exam = _exam(
        [
            _question(
                5,
                1,
                "Ist das wahr?",
                options=["A) Wahr", "B) Falsch"],
                qtype="single_choice",
            )
        ]
    )
    students = [
        {
            "e-mail-adresse": "a@example.ch",
            "frage1": "Ist das wahr?",
            "antwort1": "vielleicht",
        },
        {
            "e-mail-adresse": "b@example.ch",
            "frage1": "Ist das wahr?",
            "antwort1": "keine ahnung",
        },
    ]
    payload = _parse(students, exam)
    # Import still succeeds (non-fatal); both attempts present.
    assert len(payload.attempts) == 2
    # Exactly ONE aggregated warning for the column, carrying the count of 2.
    option_warnings = [w for w in payload.warnings if "Antwortoption" in w]
    assert len(option_warnings) == 1
    assert "Frage 1" in option_warnings[0] and "2 Antwort" in option_warnings[0]


def test_matching_choice_answer_emits_no_warning():
    exam = _exam(
        [
            _question(
                5,
                1,
                "Ist das wahr?",
                options=["A) Wahr", "B) Falsch"],
                qtype="single_choice",
            )
        ]
    )
    student = {
        "e-mail-adresse": "a@example.ch",
        "frage1": "Ist das wahr?",
        "antwort1": "A) Wahr",
    }
    payload = _parse([student], exam)
    assert not [w for w in payload.warnings if "Antwortoption" in w]


# ---------------------------------------------------------------------------
# Idempotency key — content-hash fallback when started_at is missing
# ---------------------------------------------------------------------------
def test_source_attempt_id_without_start_uses_content_hash():
    exam = _exam([_question(1, 1, "Frage A")])
    student = {"e-mail-adresse": "a@example.ch", "frage1": "Frage A", "antwort1": "x"}
    sid = _parse([student], exam).attempts[0].source_attempt_id
    assert sid.startswith("a@example.ch|h:")
    # Deterministic across re-parses (idempotent re-import).
    assert sid == _parse([student], exam).attempts[0].source_attempt_id


def test_timestampless_key_is_stable_under_row_reordering():
    """Without a start time the key must NOT depend on row order — otherwise a
    re-export in a different order would skip a genuinely new attempt."""
    exam = _exam([_question(1, 1, "Frage A")])
    a = {"e-mail-adresse": "a@example.ch", "frage1": "Frage A", "antwort1": "x"}
    b = {"e-mail-adresse": "b@example.ch", "frage1": "Frage A", "antwort1": "y"}
    forward = {
        att.student_external_id: att.source_attempt_id
        for att in _parse([a, b], exam).attempts
    }
    reverse = {
        att.student_external_id: att.source_attempt_id
        for att in _parse([b, a], exam).attempts
    }
    assert forward == reverse


def test_distinct_answers_without_start_yield_distinct_keys():
    exam = _exam([_question(1, 1, "Frage A")])
    students = [
        {
            "e-mail-adresse": "a@example.ch",
            "frage1": "Frage A",
            "antwort1": "antwort-eins",
        },
        {
            "e-mail-adresse": "a@example.ch",
            "frage1": "Frage A",
            "antwort1": "antwort-zwei",
        },
    ]
    ids = [att.source_attempt_id for att in _parse(students, exam).attempts]
    assert len(set(ids)) == 2
