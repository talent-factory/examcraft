"""Notenexport — drei Formate (CSV / Moodle-CSV / PDF) per Spec 9.

Pattern wie ``services.exam_export_service``: stateless Exporter-Klassen,
einer pro Format. Der Service-Module gibt drei Klassen frei:

* ``GradeCsvExporter`` — UTF-8 CSV mit ``;``-Delimiter, deutscher Header
  ("external_id;display_name;Punkte;Maximalpunkte;Prozent;Note;Status").
* ``MoodleGradeCsvExporter`` — Moodle-Grades-Reimport-Format. Spalten
  ``"Email address";"State";"Grade/X.0"`` und Punkte-Skala an Moodles
  ``X.0``-Konvention angepasst, sodass die Datei direkt im Moodle-
  Gradebook hochgeladen werden kann.
* ``GradePdfExporter`` — reportlab-PDF mit Header (Institution /
  Prüfung / Datum), tabellarisch, Footer mit Lehrperson-Signatur-Feld.

Alle Exporter nehmen ein vorbereitetes ``GradeExportData``-DTO entgegen
— der API-Layer baut das Objekt einmal aus der DB zusammen, jeder
Exporter rendert es. Vermeidet, dass jedes Format dieselben Joins
schreiben muss.

Note-Berechnung: ``GradingSchemeEvaluator.percentage_to_grade`` —
``scheme_config = None`` → fällt auf "—" zurück (statt zu crashen, wenn
die Lehrperson noch keine Skala zugeordnet hat).
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
# DTOs — der API-Layer baut diese aus DB zusammen, alle Exporter teilen sie
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GradeRow:
    external_id: str
    display_name: str | None
    total_points_awarded: float
    total_points_max: float
    percentage: float
    grade_status: str
    moodle_state: str | None = None  # Optional: Moodle "State"-Spalte


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
    set so a missing skala doesn't crash the export.
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
    """Default CSV — Excel-friendly, ``;`` delimiter, BOM für Excel-DE."""

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
    """Moodle-Grades-Reimport Format.

    Moodles "Import: CSV file" feature on Quiz-Grades-Page erwartet:

    * ``"Email address"`` — eindeutiger Identifier (Spec: external_id
      = E-Mail per Default; falls nicht E-Mail, schreibt der Exporter
      die external_id als Fallback in dieselbe Spalte und Moodle
      verweigert dann den Import — bewusste Sicherheits-Abweisung).
    * ``"State"`` — ``"Finished"`` für submitted attempts (im import_
      pipeline normalisiert), sonst leer.
    * ``"Grade/X.0"`` — die Note-Spalte. ``X`` ist die Maximalpunktzahl
      der Prüfung, mit ``.0``-Suffix (Moodle-Konvention).

    Die Skala wird in Punkten exportiert (nicht als Note-Label) — Moodle
    rechnet selbst. Für stepped-Schemes wo es keine numerischen Punkte
    gibt fallen wir auf percentage zurück (Moodle akzeptiert Dezimal-
    werte in dieser Spalte).
    """

    @staticmethod
    def export(data: GradeExportData) -> bytes:
        if not data.rows:
            # Empty-Datei mit Header so Moodle erkennt das Format
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
    """PDF Notenliste mit Institution-Header, Tabelle und Signatur-Footer."""

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

        # --- Footer (Signatur)
        story.append(
            Paragraph(
                "Lehrperson: ____________________________&nbsp;&nbsp;"
                "Unterschrift: ____________________________",
                styles["Normal"],
            )
        )

        doc.build(story)
        return buffer.getvalue()
