"""Tests for MoodleCsvDriver.

Pure parser tests with no DB. ``Exam`` is built as a
``SimpleNamespace`` stub; that satisfies the ``ExamLike`` protocol.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.import_drivers import (
    EmptyCsvError,
    MissingColumnError,
    MoodleCsvDriver,
)
from services.import_drivers.moodle_csv_driver import (
    _OVERFLOW_KEY,
    _parse_datetime,
    _parse_german_long_date,
)


FIXTURES = Path(__file__).parent / "fixtures" / "moodle_csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_exam(num_questions: int = 3, exam_id: int = 42):
    """Stub-Exam mit ExamQuestion-likes (id, position)."""
    questions = [
        SimpleNamespace(id=100 + i, position=i + 1) for i in range(num_questions)
    ]
    return SimpleNamespace(id=exam_id, questions=questions)


CSV_DE_SEMI = (
    "Vorname;Nachname;E-Mail-Adresse;Status;Begonnen am;Beendet;"
    "Antwort 1;Antwort 2;Antwort 3\n"
    "Anna;Beispiel;anna@example.org;Beendet;2026-04-30 09:00:00;"
    "2026-04-30 09:30:00;A;Wahr;Berlin\n"
    "Bruno;Muster;bruno@example.org;Beendet;2026-04-30 09:00:00;"
    "2026-04-30 09:25:00;C;Falsch;Madrid\n"
)

CSV_EN_COMMA = (
    "First name,Surname,Email address,State,Started on,Completed,"
    "Response 1,Response 2,Response 3\n"
    "Anna,Beispiel,anna@example.org,Finished,2026-04-30 09:00:00,"
    "2026-04-30 09:30:00,A,True,Berlin\n"
    "Bruno,Muster,bruno@example.org,Finished,2026-04-30 09:00:00,"
    "2026-04-30 09:25:00,C,False,Madrid\n"
)


# ---------------------------------------------------------------------------
# Locale + Trenner
# ---------------------------------------------------------------------------


def test_parses_german_semicolon_csv() -> None:
    payload = MoodleCsvDriver().parse(CSV_DE_SEMI, exam=make_exam())

    assert payload.exam_id == 42
    assert payload.driver_name == "moodle_csv"
    assert len(payload.students) == 2
    assert {s.external_id for s in payload.students} == {
        "anna@example.org",
        "bruno@example.org",
    }
    assert payload.source_metadata["delimiter"] == ";"
    assert payload.errors == []
    # Anna's Antwort 1 -> exam_question_id 100, position 1
    anna_attempts = [
        a for a in payload.attempts if a.student_external_id == "anna@example.org"
    ]
    assert len(anna_attempts) == 1
    answers_by_qid = {
        a.exam_question_id: a.given_answer for a in anna_attempts[0].answers
    }
    assert answers_by_qid == {100: "A", 101: "Wahr", 102: "Berlin"}


def test_parses_english_comma_csv() -> None:
    payload = MoodleCsvDriver().parse(CSV_EN_COMMA, exam=make_exam())

    assert len(payload.students) == 2
    assert payload.source_metadata["delimiter"] == ","
    bruno = [
        a for a in payload.attempts if a.student_external_id == "bruno@example.org"
    ][0]
    assert bruno.answers[1].given_answer == "False"


def test_parses_tab_separated_csv() -> None:
    """``\\t`` is a contracted separator — the driver advertises it in
    its docstring and ``csv.Sniffer`` config, so ensure it's actually
    exercised."""
    csv_tsv = "E-Mail-Adresse\tAntwort 1\tAntwort 2\nanna@example.org\tBern\tWahr\n"
    payload = MoodleCsvDriver().parse(csv_tsv, exam=make_exam(num_questions=2))
    assert payload.source_metadata["delimiter"] == "\t"
    assert len(payload.students) == 1
    assert [a.given_answer for a in payload.attempts[0].answers] == ["Bern", "Wahr"]


def test_decodes_utf8_bom() -> None:
    payload = MoodleCsvDriver().parse(
        ("﻿" + CSV_DE_SEMI).encode("utf-8"), exam=make_exam()
    )
    assert len(payload.students) == 2


# ---------------------------------------------------------------------------
# Spalten-Toleranz
# ---------------------------------------------------------------------------


def test_missing_email_column_raises_hard_error() -> None:
    csv_text = "Vorname;Nachname;Status;Antwort 1\nAnna;Beispiel;Beendet;A\n"
    with pytest.raises(MissingColumnError):
        MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))


def test_missing_optional_columns_are_tolerated() -> None:
    """Ohne Vorname/Nachname/Started/Completed importiert der Driver
    trotzdem; display_name bleibt None, Datums NULL."""
    csv_text = "E-Mail-Adresse;Antwort 1\nanna@example.org;A\n"
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))

    assert len(payload.students) == 1
    assert payload.students[0].display_name is None
    assert payload.attempts[0].started_at is None
    assert payload.attempts[0].submitted_at is None


def test_no_answer_columns_emits_warning() -> None:
    csv_text = "Vorname;Nachname;E-Mail-Adresse\nAnna;Beispiel;anna@example.org\n"
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam())

    assert any("Keine Antwort-Spalten" in w for w in payload.warnings)
    assert payload.attempts[0].answers == []


def test_column_count_mismatch_warns() -> None:
    """Mehr Antwort-Spalten als Fragen → Warnung, aber Persistenz für
    valide Positionen läuft durch."""
    csv_text = (
        "E-Mail-Adresse;Antwort 1;Antwort 2;Antwort 3;Antwort 4\n"
        "anna@example.org;A;B;C;D\n"
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=2))

    assert any("Spaltenanzahl" in w for w in payload.warnings)
    # Position 3 und 4 haben keine Frage:
    assert any("Position 3" in w for w in payload.warnings)
    assert any("Position 4" in w for w in payload.warnings)
    # Es werden trotzdem 2 Antworten persistiert (Pos 1 + 2):
    assert len(payload.attempts[0].answers) == 2


def test_answer_columns_in_arbitrary_order() -> None:
    """Header-Reihenfolge spielt keine Rolle, die Position aus dem
    Spaltennamen zählt."""
    csv_text = (
        "E-Mail-Adresse;Antwort 3;Antwort 1;Antwort 2\nanna@example.org;Berlin;A;Wahr\n"
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=3))

    answers = {a.exam_question_id: a.given_answer for a in payload.attempts[0].answers}
    assert answers == {100: "A", 101: "Wahr", 102: "Berlin"}


# ---------------------------------------------------------------------------
# Empty / unparseable
# ---------------------------------------------------------------------------


def test_empty_csv_raises_empty_error() -> None:
    with pytest.raises(EmptyCsvError):
        MoodleCsvDriver().parse("", exam=make_exam())


def test_header_only_csv_raises_empty_error() -> None:
    csv_text = "E-Mail-Adresse;Antwort 1\n"
    with pytest.raises(EmptyCsvError):
        MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))


def test_latin1_input_decodes_and_warns() -> None:
    """Non-UTF-8 inputs (Moodle's Windows-Excel exports) decode cleanly
    and produce a visible warning so the operator notices the fallback.

    The decoder tries cp1252 *before* latin-1 (cp1252 is what Excel
    actually emits), so the encoding flag may report either.
    """
    csv_latin = ("E-Mail-Adresse;Antwort 1\nmüller@example.org;Berlin\n").encode(
        "latin-1"
    )
    payload = MoodleCsvDriver().parse(csv_latin, exam=make_exam(num_questions=1))

    assert payload.students[0].external_id == "müller@example.org"
    assert payload.source_metadata["encoding"] in ("cp1252", "latin-1")
    assert any("Encoding-Fallback" in w for w in payload.warnings)


def test_garbled_bytes_do_not_crash_driver() -> None:
    """Adversarial byte salad must not abort the entire process. The
    driver either raises a typed ImportDriverError (binary-sniff catches
    it, or the latin-1 fallback yields garbage that hits MissingColumnError)
    — never an unhandled error.
    """
    from services.import_drivers.base import ImportDriverError

    bad = b"\xc3\x28invalid"
    with pytest.raises(ImportDriverError):
        MoodleCsvDriver().parse(bad, exam=make_exam())


# ---------------------------------------------------------------------------
# Pro-Row-Toleranz
# ---------------------------------------------------------------------------


def test_row_with_empty_email_is_skipped() -> None:
    csv_text = "E-Mail-Adresse;Antwort 1\n;A\nanna@example.org;B\n"
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))

    assert len(payload.students) == 1
    assert payload.students[0].external_id == "anna@example.org"
    assert len(payload.errors) == 1
    assert payload.errors[0].row_index == 2
    assert "external_id" in payload.errors[0].reason.lower()


def test_row_with_surplus_columns_is_imported_not_dropped() -> None:
    """A row with more fields than the header (an extra exported column,
    a stray delimiter, or broken quoting) makes ``csv.DictReader`` collect
    the surplus values under the ``restkey`` — whose default is ``None``.
    ``raw_payload: dict[str, Any]`` then rejects the ``None`` key
    (Pydantic: keys must be ``str``) and the row was rejected as a
    row-level error instead of being imported (TF-411). The row must
    instead be imported, the overflow surfaced as a warning, and
    ``raw_payload`` carry only string keys.
    """
    # Quoted fields so csv.Sniffer locks onto ';' via its quote
    # heuristic (the frequency heuristic bails on ragged rows). Bruno's
    # row carries one surplus field ("Spanien") beyond the 9-column
    # header → DictReader files it under the None restkey.
    csv_text = (
        '"Vorname";"Nachname";"E-Mail-Adresse";"Status";"Begonnen am";'
        '"Beendet";"Antwort 1";"Antwort 2";"Antwort 3"\n'
        '"Anna";"Beispiel";"anna@example.org";"Beendet";'
        '"2026-04-30 09:00:00";"2026-04-30 09:30:00";"A";"Wahr";"Berlin"\n'
        '"Bruno";"Muster";"bruno@example.org";"Beendet";'
        '"2026-04-30 09:00:00";"2026-04-30 09:25:00";"C";"Falsch";'
        '"Madrid";"Spanien"\n'
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=3))

    # Both rows survive — no Pydantic crash, both attempts persisted.
    assert payload.errors == []
    assert len(payload.students) == 2
    assert len(payload.attempts) == 2
    # raw_payload must never carry a non-string (None) key.
    for attempt in payload.attempts:
        assert all(isinstance(k, str) for k in attempt.raw_payload)
    # Exactly one overflow warning for Bruno (row 3), naming the surplus
    # count and flagging possible column shift (not a benign "junk
    # ignored" message) so the operator verifies the row.
    overflow_warnings = [w for w in payload.warnings if "überzählige Spalte" in w]
    assert len(overflow_warnings) == 1
    assert "Zeile 3" in overflow_warnings[0]
    assert "1 überzählige" in overflow_warnings[0]
    assert "Spaltenverschiebung" in overflow_warnings[0]
    # In-header answers stay correctly aligned despite the overflow.
    bruno = next(
        a for a in payload.attempts if a.student_external_id == "bruno@example.org"
    )
    given = {ans.exam_question_id: ans.given_answer for ans in bruno.answers}
    assert given[102] == "Madrid"
    # The surplus value is preserved in raw_payload (recoverable) rather
    # than silently lost.
    assert bruno.raw_payload[_OVERFLOW_KEY] == ["Spanien"]


def test_row_with_fewer_columns_is_imported_without_overflow_warning() -> None:
    """The mirror of the surplus case: a row with *fewer* fields than the
    header. ``csv.DictReader`` fills the missing trailing fields with its
    ``restval`` (default ``None``), so ``raw_payload`` carries ``None``
    *values* — which ``dict[str, Any]`` accepts (only ``None`` *keys*
    crash). The row imports cleanly, missing answers become ``None``, and
    crucially NO overflow warning fires (short != surplus)."""
    csv_text = (
        '"E-Mail-Adresse";"Antwort 1";"Antwort 2";"Antwort 3"\n'
        '"anna@example.org";"A";"Wahr";"Berlin"\n'
        '"bruno@example.org";"C"\n'  # Antwort 2 + 3 absent
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=3))

    assert payload.errors == []
    assert len(payload.attempts) == 2
    bruno = next(
        a for a in payload.attempts if a.student_external_id == "bruno@example.org"
    )
    given = {ans.exam_question_id: ans.given_answer for ans in bruno.answers}
    assert given == {100: "C", 101: None, 102: None}
    # Missing headers carry None *values* in raw_payload (not a crash).
    assert bruno.raw_payload["Antwort 3"] is None
    # A short row is not an overflow — no surplus key, no overflow warning.
    assert _OVERFLOW_KEY not in bruno.raw_payload
    assert not any("überzählige Spalte" in w for w in payload.warnings)


# ---------------------------------------------------------------------------
# Mehrfachversuche + Idempotenz
# ---------------------------------------------------------------------------


def test_multiple_attempts_per_student_get_sequential_numbers() -> None:
    csv_text = (
        "E-Mail-Adresse;Begonnen am;Antwort 1\n"
        "anna@example.org;2026-04-30 09:00:00;A\n"
        "anna@example.org;2026-04-30 10:00:00;B\n"
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))

    assert len(payload.students) == 1  # gleiche external_id → ein Student
    anna_attempts = [
        a for a in payload.attempts if a.student_external_id == "anna@example.org"
    ]
    assert len(anna_attempts) == 2
    assert [a.attempt_number for a in anna_attempts] == [1, 2]


def test_explicit_attempt_column_wins_over_auto_increment() -> None:
    csv_text = (
        "E-Mail-Adresse;Versuch;Antwort 1\nanna@example.org;3;A\nanna@example.org;5;B\n"
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))

    nums = [a.attempt_number for a in payload.attempts]
    assert nums == [3, 5]


def test_source_attempt_id_is_deterministic() -> None:
    """Selbe CSV zweimal parsen → identische source_attempt_ids für
    Idempotenz."""
    payload_a = MoodleCsvDriver().parse(CSV_DE_SEMI, exam=make_exam())
    payload_b = MoodleCsvDriver().parse(CSV_DE_SEMI, exam=make_exam())

    ids_a = sorted(a.source_attempt_id for a in payload_a.attempts)
    ids_b = sorted(a.source_attempt_id for a in payload_b.attempts)
    assert ids_a == ids_b
    # ID enthält external_id + Zeitstempel + Versuchsnummer
    for sid in ids_a:
        assert "@example.org" in sid


# ---------------------------------------------------------------------------
# Datums-Formate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-04-30 09:00:00", datetime(2026, 4, 30, 9, 0, 0, tzinfo=timezone.utc)),
        ("2026-04-30 09:00", datetime(2026, 4, 30, 9, 0, tzinfo=timezone.utc)),
        ("30/04/26, 09:00", datetime(2026, 4, 30, 9, 0, tzinfo=timezone.utc)),
        ("30.04.2026, 09:00", datetime(2026, 4, 30, 9, 0, tzinfo=timezone.utc)),
        (
            "2026-04-30T09:00:00",
            datetime(2026, 4, 30, 9, 0, 0, tzinfo=timezone.utc),
        ),
    ],
)
def test_date_parsing_accepts_multiple_formats(raw: str, expected: datetime) -> None:
    csv_text = f"E-Mail-Adresse;Begonnen am;Antwort 1\nanna@example.org;{raw};A\n"
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))
    assert payload.attempts[0].started_at == expected
    # All persisted datetimes must be tz-aware UTC; mixing naïve + aware
    # in the same column makes ``min``/``max`` raise TypeError and
    # produces non-deterministic source_attempt_ids.
    assert payload.attempts[0].started_at.tzinfo is not None
    assert payload.attempts[0].started_at.utcoffset().total_seconds() == 0


# TF-411: Moodle DE exports render long-form dates with German month
# names ("12. Juni 2026 11:55"). These never parsed because (a) no
# format matched the "day-dot, no comma" shape and (b) ``%B`` is
# locale-bound and only matches English month names under the C locale.
@pytest.mark.parametrize(
    "raw,expected",
    [
        # The exact value from the prod report (no comma before time).
        ("12. Juni 2026 11:55", datetime(2026, 6, 12, 11, 55, tzinfo=timezone.utc)),
        # Comma variant (older Moodle long format).
        ("12. Juni 2026, 11:55", datetime(2026, 6, 12, 11, 55, tzinfo=timezone.utc)),
        # Single-digit day + umlaut month.
        ("1. März 2026 08:00", datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)),
        # With seconds.
        ("5. Mai 2026 09:00:30", datetime(2026, 5, 5, 9, 0, 30, tzinfo=timezone.utc)),
        # All twelve month names must map.
        ("3. Januar 2026 00:00", datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc)),
        ("3. Februar 2026 00:00", datetime(2026, 2, 3, 0, 0, tzinfo=timezone.utc)),
        ("3. April 2026 00:00", datetime(2026, 4, 3, 0, 0, tzinfo=timezone.utc)),
        ("3. Juli 2026 00:00", datetime(2026, 7, 3, 0, 0, tzinfo=timezone.utc)),
        ("3. August 2026 00:00", datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)),
        ("3. September 2026 00:00", datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc)),
        ("3. Oktober 2026 14:30", datetime(2026, 10, 3, 14, 30, tzinfo=timezone.utc)),
        ("3. November 2026 00:00", datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc)),
        (
            "24. Dezember 2026 23:59",
            datetime(2026, 12, 24, 23, 59, tzinfo=timezone.utc),
        ),
    ],
)
def test_parse_datetime_accepts_german_month_names(
    raw: str, expected: datetime
) -> None:
    parsed = _parse_datetime(raw)
    assert parsed == expected
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_german_long_date_parses_through_driver_without_warning() -> None:
    """End-to-end: a German 'Beendet' value lands in ``submitted_at``
    and no 'nicht parsbar' warning is emitted (TF-411 Problem 2)."""
    csv_text = (
        "E-Mail-Adresse;Begonnen am;Beendet;Antwort 1\n"
        "anna@example.org;12. Juni 2026 11:50;12. Juni 2026 11:55;A\n"
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))
    assert payload.attempts[0].started_at == datetime(
        2026, 6, 12, 11, 50, tzinfo=timezone.utc
    )
    assert payload.attempts[0].submitted_at == datetime(
        2026, 6, 12, 11, 55, tzinfo=timezone.utc
    )
    assert not any("nicht parsbar" in w for w in payload.warnings)


@pytest.mark.parametrize(
    "raw",
    [
        "31. Februar 2026 10:00",  # regex matches, calendar-invalid → ValueError
        "12. Foo 2026 11:55",  # regex matches, unknown month name
        "12. Juni 2026 25:00",  # regex matches, out-of-range hour
    ],
)
def test_parse_german_long_date_rejects_invalid_values(raw: str) -> None:
    """Shape matches the regex but the value is not a real date — the two
    guard branches (unknown month, ValueError from ``datetime(...)``)
    must return None rather than a wrong/rolled-over timestamp."""
    assert _parse_german_long_date(raw) is None
    assert _parse_datetime(raw) is None


def test_invalid_german_date_warns_as_unparsable_through_driver() -> None:
    """A calendar-invalid German date reaches the same 'nicht parsbar →
    NULL' path as any other unparseable value (no silent divergence)."""
    csv_text = (
        '"E-Mail-Adresse";"Beendet";"Antwort 1"\n'
        '"anna@example.org";"31. Februar 2026 10:00";"A"\n'
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))
    assert payload.attempts[0].submitted_at is None
    assert any(
        "Zeile 2" in w and "'Beendet' nicht parsbar" in w for w in payload.warnings
    )


@pytest.mark.parametrize(
    "raw",
    [
        "2026-04-30 09:00:00",
        "2026-04-30 09:00",
        "30/04/2026, 09:00",
        "30.04.2026, 09:00",
        "2026-04-30T09:00:00",
        "2026-04-30T09:00:00Z",
        "2026-04-30T09:00:00+02:00",
    ],
)
def test_parse_datetime_always_returns_utc_aware(raw: str) -> None:
    parsed = _parse_datetime(raw)
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_unrecognised_date_returns_none_and_warns() -> None:
    """A non-empty but unparseable date column surfaces as a warning so
    the operator sees their timestamps were silently dropped."""
    csv_text = "E-Mail-Adresse;Begonnen am;Antwort 1\nanna@example.org;not-a-date;A\n"
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))
    assert payload.attempts[0].started_at is None
    assert any("Begonnen am" in w and "nicht parsbar" in w for w in payload.warnings)


def test_non_numeric_attempt_column_warns() -> None:
    """An unparseable 'Versuch' value falls back to auto-increment but
    must produce a warning — otherwise the operator thinks their
    explicit numbers were honoured."""
    csv_text = (
        "E-Mail-Adresse;Versuch;Antwort 1\n"
        "anna@example.org;3a;A\n"  # '3a' not parseable
    )
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))
    # Auto-increment took over: attempt_number 1
    assert payload.attempts[0].attempt_number == 1
    assert any(
        "nicht-numerischen" in w or "nicht-numerisch" in w for w in payload.warnings
    )


def test_sniffer_fallback_warns_on_ambiguous_input() -> None:
    """When csv.Sniffer fails we fall back to comma. The fallback emits
    a warning so misparsed semicolon CSVs are diagnosable."""
    # Single-cell-per-row CSV trips the sniffer's heuristic.
    csv_ambiguous = "E-Mail-Adresse\nanna@example.org\n"
    payload = MoodleCsvDriver().parse(csv_ambiguous, exam=make_exam(num_questions=0))
    # Ambiguous inputs may or may not hit the fallback depending on
    # csv.Sniffer's Python version; assert behaviourally — when fallback
    # fires, the metadata flag is True and a warning exists.
    if payload.source_metadata.get("sniffer_fallback"):
        assert any("Trenner-Erkennung" in w for w in payload.warnings)


# ---------------------------------------------------------------------------
# Whitespace / Case
# ---------------------------------------------------------------------------


def test_header_whitespace_is_tolerated() -> None:
    """CSV-Header mit zusätzlichen Leerzeichen werden trotzdem erkannt."""
    csv_text = "  E-Mail-Adresse  ; Antwort  1 ;Antwort 2\nanna@example.org;A;B\n"
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=2))

    assert len(payload.students) == 1
    assert len(payload.attempts[0].answers) == 2


def test_email_column_case_insensitive() -> None:
    csv_text = "EMAIL ADDRESS;Antwort 1\nanna@example.org;A\n"
    payload = MoodleCsvDriver().parse(csv_text, exam=make_exam(num_questions=1))
    assert payload.students[0].external_id == "anna@example.org"


def test_raw_payload_is_preserved() -> None:
    """raw_payload enthält die Originalzeile als dict für Traceability."""
    payload = MoodleCsvDriver().parse(CSV_DE_SEMI, exam=make_exam())
    raw = payload.attempts[0].raw_payload
    assert raw["E-Mail-Adresse"] == "anna@example.org"
    assert raw["Antwort 1"] == "A"


def test_encoding_metadata_records_chosen_encoding() -> None:
    """``source_metadata['encoding']`` exposes which decoder won so the
    operator can spot a non-UTF-8 source from the import job."""
    payload_str = MoodleCsvDriver().parse(CSV_DE_SEMI, exam=make_exam())
    assert payload_str.source_metadata["encoding"] == "str"

    payload_bom = MoodleCsvDriver().parse(
        ("﻿" + CSV_DE_SEMI).encode("utf-8"), exam=make_exam()
    )
    assert payload_bom.source_metadata["encoding"] == "utf-8-sig"


# ---------------------------------------------------------------------------
# Realistische Moodle-Fixtures (DoD: "realistische Moodle-CSV-Beispiele")
# ---------------------------------------------------------------------------


def test_realistic_german_moodle_export_parses_cleanly() -> None:
    """DoD-Anker: die DE-Fixture aus tests/fixtures/moodle_csv/ wird vom
    Driver vollständig geparst (5 Studierende, 5 Versuche, keine Pro-Row-
    Errors)."""
    raw_bytes = (FIXTURES / "quiz_responses_de.csv").read_bytes()
    payload = MoodleCsvDriver().parse(raw_bytes, exam=make_exam(num_questions=3))

    assert payload.errors == []
    assert len(payload.students) == 5
    assert len(payload.attempts) == 5
    # Antwort-Texte werden vollständig durchgereicht (auch Umlaute).
    anna = next(
        a
        for a in payload.attempts
        if a.student_external_id == "anna.beispiel@example.org"
    )
    answers = {ans.exam_question_id: ans.given_answer for ans in anna.answers}
    assert answers == {
        100: "Bern",
        101: "Wahr",
        102: (
            "Föderalismus bedeutet, dass Bund, Kantone und Gemeinden je "
            "eigene Aufgaben und Steuerhoheit haben."
        ),
    }


def test_realistic_english_moodle_export_parses_cleanly() -> None:
    raw_bytes = (FIXTURES / "quiz_responses_en.csv").read_bytes()
    payload = MoodleCsvDriver().parse(raw_bytes, exam=make_exam(num_questions=3))

    assert payload.errors == []
    assert len(payload.students) == 3
    assert len(payload.attempts) == 3
    alice = next(
        a
        for a in payload.attempts
        if a.student_external_id == "alice.smith@example.org"
    )
    assert alice.answers[0].given_answer == "Bern"
    assert alice.answers[1].given_answer == "True"


# ---------------------------------------------------------------------------
# Embedded newlines + quoted fields (open-ended answers)
# ---------------------------------------------------------------------------


def test_quoted_field_with_embedded_newline_does_not_corrupt_next_row() -> None:
    """Open-ended Moodle answers commonly include newlines.

    csv.DictReader honours RFC 4180 quoting, so a quoted multi-line answer
    must not bleed into the next row. This test would fail if anyone
    swapped the parser for a naive split-on-newline.
    """
    csv = (
        "Vorname;Nachname;E-Mail-Adresse;Begonnen am;Beendet;"
        "Antwort 1;Antwort 2;Antwort 3\n"
        "Anna;Beispiel;anna@example.org;2026-04-30 09:00:00;"
        "2026-04-30 09:30:00;A;Wahr;"
        '"line one\nline two\nline three"\n'
        "Bruno;Muster;bruno@example.org;2026-04-30 09:00:00;"
        "2026-04-30 09:25:00;C;Falsch;Eine Zeile\n"
    )
    payload = MoodleCsvDriver().parse(csv, exam=make_exam(num_questions=3))

    assert payload.errors == []
    assert len(payload.students) == 2
    assert len(payload.attempts) == 2
    anna = next(
        a for a in payload.attempts if a.student_external_id == "anna@example.org"
    )
    bruno = next(
        a for a in payload.attempts if a.student_external_id == "bruno@example.org"
    )
    assert "\n" in (anna.answers[2].given_answer or "")
    assert (bruno.answers[2].given_answer or "").strip() == "Eine Zeile"


def test_quoted_field_with_embedded_semicolon_does_not_split() -> None:
    """A semicolon inside a quoted field must not split the row."""
    csv = (
        "Vorname;Nachname;E-Mail-Adresse;Begonnen am;Beendet;"
        "Antwort 1;Antwort 2;Antwort 3\n"
        "Anna;Beispiel;anna@example.org;2026-04-30 09:00:00;"
        "2026-04-30 09:30:00;A;Wahr;"
        '"first; second; third"\n'
    )
    payload = MoodleCsvDriver().parse(csv, exam=make_exam(num_questions=3))
    assert payload.errors == []
    anna = next(a for a in payload.attempts)
    assert anna.answers[2].given_answer == "first; second; third"


# ---------------------------------------------------------------------------
# Encoding-Sniff: binäre Eingaben werden klar abgewiesen
# ---------------------------------------------------------------------------


def test_binary_input_is_rejected_with_clear_error() -> None:
    """Latin-1 always decodes any byte sequence — without a binary sniff
    a PDF/Excel upload would produce an opaque "no datarows" error."""
    from services.import_drivers import UnparseableCsvError

    # PDF magic bytes + null bytes
    binary = b"%PDF-1.4\n" + bytes([0, 1, 2, 3] * 1024)
    with pytest.raises(UnparseableCsvError, match="binär"):
        MoodleCsvDriver().parse(binary, exam=make_exam(num_questions=3))


def test_cp1252_export_decodes_with_warning() -> None:
    """Windows-Excel exports are cp1252 — must decode cleanly without
    mojibake but still warn the operator that the encoding wasn't UTF-8."""
    csv_text = (
        "Vorname;Nachname;E-Mail-Adresse;Begonnen am;Beendet;Antwort 1\n"
        "Annaüöä;Beispiel;anna@example.org;2026-04-30 09:00:00;"
        "2026-04-30 09:30:00;A\n"
    )
    raw = csv_text.encode("cp1252")
    payload = MoodleCsvDriver().parse(raw, exam=make_exam(num_questions=1))
    assert payload.errors == []
    assert any("Encoding-Fallback" in w for w in payload.warnings)
    anna = payload.attempts[0]
    # Umlaute survive the round-trip
    assert anna.student_external_id == "anna@example.org"
    name = next(s for s in payload.students if s.external_id == "anna@example.org")
    assert name.display_name and "üöä" in name.display_name
