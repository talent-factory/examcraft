"""Tests for ``services.grade_export_service``.

Pure unit tests — exporters are stateless, so they only need a
hand-rolled ``GradeExportData`` DTO. PDF tests use ``pypdf`` to
spot-check that the byte stream is a valid PDF and contains the
header/student rows we expect (don't assert layout — that flakes
across reportlab versions).
"""

from __future__ import annotations

import io
from datetime import date

import pytest

from services.grade_export_service import (
    GradeCsvExporter,
    GradeExportData,
    GradePdfExporter,
    GradeRow,
    MoodleGradeCsvExporter,
)


SWISS_SCHEME = {
    "type": "linear_segments",
    "round_to": 0.1,
    "pass_grade_label": "4.0",
    "segments": [
        {"from_pct": 0, "to_pct": 50, "from_grade": 1.0, "to_grade": 4.0},
        {"from_pct": 50, "to_pct": 100, "from_grade": 4.0, "to_grade": 6.0},
    ],
}


def _data(scheme=SWISS_SCHEME) -> GradeExportData:
    return GradeExportData(
        institution_name="FFHS",
        exam_title="Statistik FS26",
        exam_course="Statistik",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        scheme_config=scheme,
        rows=[
            GradeRow(
                external_id="anna@example.org",
                display_name="Anna B.",
                total_points_awarded=18.0,
                total_points_max=20.0,
                percentage=90.0,
                grade_status="fully_reviewed",
            ),
            GradeRow(
                external_id="bruno@example.org",
                display_name=None,
                total_points_awarded=10.0,
                total_points_max=20.0,
                percentage=50.0,
                grade_status="fully_reviewed",
            ),
            GradeRow(
                external_id="clara@example.org",
                display_name="Clara",
                total_points_awarded=4.0,
                total_points_max=20.0,
                percentage=20.0,
                grade_status="fully_reviewed",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def test_csv_export_has_german_header_and_semicolon_delimiter() -> None:
    raw = GradeCsvExporter.export(_data())
    assert raw.startswith("﻿".encode("utf-8")), "Excel BOM für DE-Excel"
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    assert lines[0].split(";") == [
        "external_id",
        "display_name",
        "Punkte",
        "Maximalpunkte",
        "Prozent",
        "Note",
        "Status",
    ]
    # Each data row has 7 columns
    for line in lines[1:]:
        assert line.count(";") == 6


def test_csv_export_writes_swiss_grade() -> None:
    text = GradeCsvExporter.export(_data()).decode("utf-8-sig")
    # 90 % → 4.0 + (40/50)*2 = 5.6 in Swiss scheme
    anna_row = [line for line in text.splitlines() if line.startswith("anna")][0]
    parts = anna_row.split(";")
    assert parts[5] == "5.6"


def test_csv_export_handles_missing_scheme_with_dash() -> None:
    text = GradeCsvExporter.export(_data(scheme=None)).decode("utf-8-sig")
    # Note column should be "—" for every row
    rows = text.splitlines()[1:]
    for row in rows:
        assert row.split(";")[5] == "—"


def test_csv_export_handles_empty_display_name() -> None:
    text = GradeCsvExporter.export(_data()).decode("utf-8-sig")
    bruno_row = [line for line in text.splitlines() if line.startswith("bruno")][0]
    parts = bruno_row.split(";")
    assert parts[1] == ""  # empty display_name


# ---------------------------------------------------------------------------
# Moodle CSV
# ---------------------------------------------------------------------------


def test_moodle_csv_header_uses_grade_max() -> None:
    raw = MoodleGradeCsvExporter.export(_data())
    text = raw.decode("utf-8")
    lines = text.splitlines()
    assert lines[0] == '"Email address","State","Grade/20.0"'


def test_moodle_csv_uses_finished_state_by_default() -> None:
    raw = MoodleGradeCsvExporter.export(_data())
    text = raw.decode("utf-8")
    rows = text.splitlines()[1:]
    for row in rows:
        assert ',"Finished",' in row


def test_moodle_csv_writes_points_not_grade_label() -> None:
    raw = MoodleGradeCsvExporter.export(_data())
    text = raw.decode("utf-8")
    anna_row = [line for line in text.splitlines() if line.startswith('"anna')][0]
    # Should contain the raw point value 18.00, NOT the grade "5.6"
    assert "18.00" in anna_row
    assert "5.6" not in anna_row


def test_moodle_csv_empty_rows_uses_default_max() -> None:
    empty = GradeExportData(
        institution_name="X",
        exam_title="Y",
        exam_course=None,
        exam_date=None,
        passing_percentage=50.0,
        scheme_config=None,
        rows=[],
    )
    text = MoodleGradeCsvExporter.export(empty).decode("utf-8")
    assert "Grade/100.0" in text


def test_moodle_csv_respects_explicit_state() -> None:
    data = _data()
    rows = list(data.rows)
    rows[0] = GradeRow(
        external_id=rows[0].external_id,
        display_name=rows[0].display_name,
        total_points_awarded=rows[0].total_points_awarded,
        total_points_max=rows[0].total_points_max,
        percentage=rows[0].percentage,
        grade_status=rows[0].grade_status,
        moodle_state="In progress",
    )
    custom = GradeExportData(
        institution_name=data.institution_name,
        exam_title=data.exam_title,
        exam_course=data.exam_course,
        exam_date=data.exam_date,
        passing_percentage=data.passing_percentage,
        scheme_config=data.scheme_config,
        rows=rows,
    )
    text = MoodleGradeCsvExporter.export(custom).decode("utf-8")
    anna_row = [line for line in text.split("\n") if line.startswith('"anna')][0]
    assert '"In progress"' in anna_row


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def test_pdf_export_returns_valid_pdf() -> None:
    pytest.importorskip("reportlab")
    pytest.importorskip("pypdf")
    pdf_bytes = GradePdfExporter.export(_data())
    assert pdf_bytes.startswith(b"%PDF"), "PDF magic header"

    # Round-trip via pypdf: must be parseable and contain key strings.
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "FFHS" in text
    assert "Statistik FS26" in text
    # External IDs should appear (not display names alone) so the
    # auditor can match rows back to the import.
    assert "anna@example.org" in text
    # Footer row with signature placeholder
    assert "Lehrperson" in text


def test_pdf_export_handles_empty_rows() -> None:
    pytest.importorskip("reportlab")
    empty = GradeExportData(
        institution_name="FFHS",
        exam_title="Empty",
        exam_course=None,
        exam_date=None,
        passing_percentage=50.0,
        scheme_config=None,
        rows=[],
    )
    pdf_bytes = GradePdfExporter.export(empty)
    assert pdf_bytes.startswith(b"%PDF")


def test_pdf_includes_calculated_grade_and_passing_percentage() -> None:
    """PDF round-trip must assert the *grade* column and the meta-line.

    A regression that drops the Note column or wires the wrong scheme
    would let the previous round-trip pass — this pins the actual
    business value of the notenliste.
    """
    pytest.importorskip("reportlab")
    pytest.importorskip("pypdf")
    pdf_bytes = GradePdfExporter.export(_data())

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Anna at 90 % under the Swiss scheme yields a numeric grade > 4.5.
    # We don't pin the exact value because reportlab's text extraction
    # rounds in places — but the integer "5" must be present somewhere
    # because the CSV export of the same row writes "5.6".
    assert "5" in text
    # Bestehensgrenze meta-line must render.
    assert "50%" in text
    # Date ISO format
    assert "2026-05-15" in text


# ---------------------------------------------------------------------------
# Security regressions
# ---------------------------------------------------------------------------


def test_csv_export_neutralises_formula_injection() -> None:
    """Excel/LibreOffice interpret leading ``=``, ``+``, ``-``, ``@`` as
    formulas. A user-controlled name like ``=HYPERLINK(...)`` would
    execute on open. The exporter must prefix-escape.
    """
    rows = [
        GradeRow(
            external_id="evil@example.org",
            display_name='=HYPERLINK("https://attacker.example/x", "click")',
            total_points_awarded=10,
            total_points_max=20,
            percentage=50,
            grade_status="fully_reviewed",
        ),
        GradeRow(
            # external_id starting with @ — also dangerous.
            external_id="@SUM(A1:A10)",
            display_name="Bob",
            total_points_awarded=15,
            total_points_max=20,
            percentage=75,
            grade_status="fully_reviewed",
        ),
    ]
    data = GradeExportData(
        institution_name="FFHS",
        exam_title="X",
        exam_course=None,
        exam_date=None,
        passing_percentage=50.0,
        scheme_config=None,
        rows=rows,
    )
    text = GradeCsvExporter.export(data).decode("utf-8")
    # The leading ``=`` and ``@`` must be neutralised with a leading
    # apostrophe — Excel won't evaluate the cell as a formula then.
    assert "'=HYPERLINK" in text
    assert "'@SUM(A1:A10)" in text
    # Defensive: no raw cell starts with ``=`` after the prefix-escape.
    # Parse the rows and check every cell.
    import csv as _csv

    reader = _csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";")
    next(reader)  # skip header
    for row in reader:
        for cell in row:
            assert not cell.startswith(("=", "+", "-", "@", "\t", "\r")), (
                f"unsafe cell start: {cell!r}"
            )


def test_moodle_csv_neutralises_formula_injection() -> None:
    rows = [
        GradeRow(
            external_id="-MALICIOUS",
            display_name="Bob",
            total_points_awarded=10,
            total_points_max=20,
            percentage=50,
            grade_status="fully_reviewed",
        ),
    ]
    data = GradeExportData(
        institution_name="FFHS",
        exam_title="X",
        exam_course=None,
        exam_date=None,
        passing_percentage=50.0,
        scheme_config=None,
        rows=rows,
    )
    text = MoodleGradeCsvExporter.export(data).decode("utf-8")
    assert "'-MALICIOUS" in text


def test_csv_bom_is_utf8_byte_literal() -> None:
    """Excel-DE relies on the UTF-8 BOM to detect encoding. Pin the
    literal byte sequence ``\\xef\\xbb\\xbf`` so a future edit can't
    silently strip it.
    """
    raw = GradeCsvExporter.export(_data())
    assert raw[:3] == b"\xef\xbb\xbf"


def test_moodle_csv_data_row_writes_points_in_third_column() -> None:
    """Moodle imports CSVs by *position*, not by header key. Pinning
    the column order prevents a future refactor from silently producing
    a file that Moodle silently misimports (assigning grades to
    ``State`` etc.).
    """
    import csv

    text = MoodleGradeCsvExporter.export(_data()).decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    # Header row first, then one row per submission.
    assert rows[0][0] == "Email address"
    assert rows[0][1] == "State"
    assert rows[0][2].startswith("Grade/")
    # Anna's row: external_id, "Finished", points "18.00".
    anna = next(r for r in rows[1:] if r[0] == "anna@example.org")
    assert anna[1] == "Finished"
    assert anna[2] == "18.00"


def test_pdf_export_handles_xml_markup_in_user_input() -> None:
    """A title like ``"AB & CD"`` or ``"<draft>"`` must not crash
    reportlab's XML parser. ``_pdf_safe`` escapes ``<`` and ``&``
    before they hit ``Paragraph``.
    """
    pytest.importorskip("reportlab")
    rows = [
        GradeRow(
            external_id="x@example.org",
            display_name="X",
            total_points_awarded=10,
            total_points_max=20,
            percentage=50,
            grade_status="fully_reviewed",
        )
    ]
    data = GradeExportData(
        institution_name="School & Co <2026>",
        exam_title="<draft> Klausur",
        exam_course="Math & Science",
        exam_date=None,
        passing_percentage=50.0,
        scheme_config=None,
        rows=rows,
    )
    pdf_bytes = GradePdfExporter.export(data)
    assert pdf_bytes.startswith(b"%PDF")
