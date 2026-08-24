"""Grade export — three formats (CSV / Moodle CSV / PDF) per Spec 9.

Same pattern as ``services.exam_export_service``: stateless exporter
classes, one per format. This service module exposes three classes:

* ``GradeCsvExporter`` — UTF-8 CSV with ``;`` delimiter, German header
  ("external_id;display_name;Punkte;Maximalpunkte;Prozent;Note;Status").
* ``MoodleGradeCsvExporter`` — Moodle grades reimport format. Columns
  ``"Email address";"State";"Grade/X.0"`` and the points scale adapted
  to Moodle's ``X.0`` convention, so the file can be uploaded directly
  into the Moodle gradebook.
* ``GradePdfExporter`` — reportlab PDF with a header (institution /
  exam / date), tabular body, footer with a teacher signature field.

All exporters take a prepared ``GradeExportData`` DTO — the API layer
builds the object once from the DB, and each exporter renders it. This
avoids every format having to write the same joins.

Grade calculation: ``GradingSchemeEvaluator.percentage_to_grade`` —
``scheme_config = None`` → falls back to "—" (instead of crashing when
the teacher hasn't assigned a grading scale yet).
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

from services.grading_scheme_evaluator import (
    GradingSchemeError,
    percentage_to_grade,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sanitizers — defensive against CSV-formula and reportlab-XML injection
# ---------------------------------------------------------------------------

# Excel/LibreOffice interpret cells starting with these characters as
# formulas. A user-controlled name like ``=HYPERLINK(...)`` would execute
# on open. Prefix the value with a leading apostrophe to neutralise.
_CSV_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value: str | None) -> str:
    """Prefix-escape a value to neutralise CSV-formula injection."""
    if not value:
        return ""
    if value.startswith(_CSV_DANGEROUS_PREFIXES):
        return "'" + value
    return value


def _pdf_safe(value: str | None) -> str:
    """Escape XML-special characters before passing into reportlab Paragraph.

    reportlab parses Paragraph content as a mini-XML dialect; raw ``<`` or
    ``&`` in user input crashes the parser. Anything containing markup
    (``<font>`` etc.) interpolated from user-controlled fields could also
    smuggle styling. Escape everything that goes into Paragraph.
    """
    if not value:
        return ""
    return _xml_escape(value, {'"': "&quot;", "'": "&apos;"})


# ---------------------------------------------------------------------------
# DTOs — the API layer builds these from the DB, shared by all exporters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GradeRow:
    external_id: str
    display_name: str | None
    total_points_awarded: float
    total_points_max: float
    percentage: float
    grade_status: str
    moodle_state: str | None = None  # Optional: Moodle "State" column


@dataclass(frozen=True)
class GradeExportData:
    institution_name: str
    exam_title: str
    exam_course: str | None
    exam_date: date | None
    passing_percentage: float
    scheme_config: dict[str, Any] | None
    rows: list[GradeRow] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _grade_label(
    percentage: float,
    scheme_config: dict[str, Any] | None,
    *,
    external_id: str | None = None,
) -> str:
    """Run the configured scheme; fall back to "—" when no scheme is
    set so a missing scale doesn't crash the export.
    """
    if scheme_config is None:
        return "—"
    try:
        return percentage_to_grade(percentage, scheme_config)
    except GradingSchemeError as exc:
        logger.warning(
            "Grading-Scheme-Eval fehlgeschlagen für %s, fallback '—': %s",
            external_id or "<unknown>",
            exc,
        )
        return "—"


def _row_label(row: GradeRow) -> str:
    return row.display_name or row.external_id


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


class GradeCsvExporter:
    """Default CSV — Excel-friendly, ``;`` delimiter, BOM for Excel-DE."""

    HEADER = [
        "external_id",
        "display_name",
        "Punkte",
        "Maximalpunkte",
        "Prozent",
        "Note",
        "Status",
    ]

    @staticmethod
    def export(data: GradeExportData) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(GradeCsvExporter.HEADER)

        for row in data.rows:
            writer.writerow(
                [
                    _csv_safe(row.external_id),
                    _csv_safe(row.display_name or ""),
                    f"{row.total_points_awarded:.2f}",
                    f"{row.total_points_max:.2f}",
                    f"{row.percentage:.2f}",
                    _csv_safe(
                        _grade_label(
                            row.percentage,
                            data.scheme_config,
                            external_id=row.external_id,
                        )
                    ),
                    _csv_safe(row.grade_status),
                ]
            )
        # UTF-8 BOM so Excel-DE doesn't mojibake the umlauts.
        return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Moodle-Grades-Reimport CSV
# ---------------------------------------------------------------------------


class MoodleGradeCsvExporter:
    """Moodle grades reimport format.

    Moodle's "Import: CSV file" feature on the quiz grades page expects:

    * ``"Email address"`` — unique identifier (spec: external_id
      = email by default; if it's not an email, the exporter writes
      the external_id as a fallback into the same column and Moodle
      then refuses the import — a deliberate safety rejection).
    * ``"State"`` — ``"Finished"`` for submitted attempts (normalized
      in the import pipeline), otherwise empty.
    * ``"Grade/X.0"`` — the grade column. ``X`` is the maximum points
      of the exam, with a ``.0`` suffix (Moodle convention).

    The scale is exported in points (not as a grade label) — Moodle
    computes on its own. For stepped schemes that have no numeric
    points, we fall back to percentage (Moodle accepts decimal values
    in this column).
    """

    @staticmethod
    def export(data: GradeExportData) -> bytes:
        if not data.rows:
            # Empty file with header so Moodle recognizes the format
            grade_max = 100.0
        else:
            grade_max = max((r.total_points_max for r in data.rows), default=100.0)

        header = [
            "Email address",
            "State",
            f"Grade/{grade_max:.1f}",
        ]

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=",", quoting=csv.QUOTE_ALL)
        writer.writerow(header)

        for row in data.rows:
            writer.writerow(
                [
                    _csv_safe(row.external_id),
                    _csv_safe(row.moodle_state or "Finished"),
                    f"{row.total_points_awarded:.2f}",
                ]
            )
        return buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


class GradePdfExporter:
    """PDF grade list with institution header, table, and signature footer."""

    @staticmethod
    def export(data: GradeExportData) -> bytes:
        # reportlab is heavy — import lazily so smoke imports of this
        # module don't pull the lib unless PDF export is actually used.
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=f"Notenliste {data.exam_title}",
        )
        styles = getSampleStyleSheet()
        story: list[Any] = []

        # --- Header
        story.append(
            Paragraph(f"<b>{_pdf_safe(data.institution_name)}</b>", styles["Title"])
        )
        story.append(
            Paragraph(
                f"Notenliste — {_pdf_safe(data.exam_title)}",
                styles["Heading2"],
            )
        )

        meta_lines: list[str] = []
        if data.exam_course:
            meta_lines.append(f"Kurs: {_pdf_safe(data.exam_course)}")
        if data.exam_date:
            meta_lines.append(f"Datum: {data.exam_date.isoformat()}")
        meta_lines.append(f"Bestehensgrenze: {data.passing_percentage:.0f}%")
        meta_lines.append(f"Erstellt am: {datetime.now().date().isoformat()}")
        story.append(Paragraph("<br/>".join(meta_lines), styles["Normal"]))
        story.append(Spacer(1, 0.6 * cm))

        # --- Table
        table_data: list[list[str]] = [
            [
                "Studi",
                "external_id",
                "Punkte",
                "Max.",
                "Prozent",
                "Note",
                "Status",
            ]
        ]
        for row in data.rows:
            table_data.append(
                [
                    _row_label(row),
                    row.external_id,
                    f"{row.total_points_awarded:.2f}",
                    f"{row.total_points_max:.2f}",
                    f"{row.percentage:.1f}%",
                    _grade_label(
                        row.percentage, data.scheme_config, external_id=row.external_id
                    ),
                    row.grade_status,
                ]
            )
        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    # Numeric columns right-aligned for readability.
                    ("ALIGN", (2, 1), (5, -1), "RIGHT"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.whitesmoke],
                    ),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 1.5 * cm))

        # --- Footer (signature)
        story.append(
            Paragraph(
                "Lehrperson: ____________________________&nbsp;&nbsp;"
                "Unterschrift: ____________________________",
                styles["Normal"],
            )
        )

        doc.build(story)
        return buffer.getvalue()
