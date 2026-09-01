"""PDF rendering for the compliance documents (TF-746).

Same pattern as ``services.grade_export_service.GradePdfExporter``:
stateless exporter classes that render a prepared DTO (here:
``compliance_content.ComplianceDocument``) via reportlab. The content
itself lives entirely in ``services.compliance_content`` — this module
only renders it, so the on-page text and the PDF can never drift
apart.
"""

from __future__ import annotations

import functools
import io
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

from services.compliance_content import ComplianceDocument


def _pdf_safe(value: str | None) -> str:
    """Escape XML-special characters before passing into reportlab Paragraph.

    See ``services.grade_export_service._pdf_safe`` for the rationale —
    reportlab parses ``Paragraph`` content as a mini-XML dialect.
    """
    if not value:
        return ""
    return _xml_escape(value, {'"': "&quot;", "'": "&apos;"})


@functools.lru_cache(maxsize=8)
def _render(document: ComplianceDocument) -> bytes:
    # Content is static and both dataclasses are frozen (hashable), so the
    # rendered PDF is byte-identical across requests — cache it rather than
    # re-running reportlab on every hit of this public, unauthenticated
    # endpoint. maxsize=8 comfortably covers avv+tom (2 documents today)
    # with headroom for future additions.
    #
    # reportlab is heavy — import lazily so smoke imports of this module
    # don't pull the lib unless a PDF export is actually requested.
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=document.title,
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph(f"<b>{_pdf_safe(document.title)}</b>", styles["Title"]))
    story.append(Paragraph(_pdf_safe(document.last_updated), styles["Normal"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(f"<i>{_pdf_safe(document.draft_notice)}</i>", styles["Normal"])
    )
    story.append(Spacer(1, 0.8 * cm))

    for section in document.sections:
        story.append(Paragraph(_pdf_safe(section.heading), styles["Heading2"]))
        for paragraph in section.paragraphs:
            story.append(Paragraph(_pdf_safe(paragraph), styles["Normal"]))
            story.append(Spacer(1, 0.2 * cm))
        story.append(Spacer(1, 0.4 * cm))

    doc.build(story)
    return buffer.getvalue()


class AvvPdfExporter:
    """Renders the Muster-AVV (``ComplianceContent.avv``) as a PDF."""

    @staticmethod
    def export(document: ComplianceDocument) -> bytes:
        return _render(document)


class TomPdfExporter:
    """Renders the TOM annex (``ComplianceContent.tom``) as a PDF."""

    @staticmethod
    def export(document: ComplianceDocument) -> bytes:
        return _render(document)
