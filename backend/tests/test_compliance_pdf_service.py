"""Tests for ``services.compliance_pdf_service`` (TF-746).

Pure unit tests — exporters take a ``ComplianceDocument`` and are
stateless. PDF tests use ``pypdf`` to spot-check that the byte stream
is a valid PDF and contains the title/draft-notice/section headings
(don't assert layout — that flakes across reportlab versions).
"""

from __future__ import annotations

import io

import pytest

from services.compliance_content import (
    ComplianceDocument,
    ComplianceSection,
    get_compliance_content,
)
from services.compliance_pdf_service import AvvPdfExporter, TomPdfExporter


def _extract_text(pdf_bytes: bytes) -> str:
    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    # reportlab wraps long headings across lines — collapse whitespace so
    # assertions check content, not where a line happened to break.
    return " ".join(raw.split())


def test_avv_exporter_produces_a_valid_pdf() -> None:
    pytest.importorskip("reportlab")
    content = get_compliance_content()

    pdf_bytes = AvvPdfExporter.export(content.avv)

    assert pdf_bytes.startswith(b"%PDF")


def test_avv_pdf_contains_title_and_draft_notice() -> None:
    pytest.importorskip("reportlab")
    content = get_compliance_content()

    text = _extract_text(AvvPdfExporter.export(content.avv))

    assert "Auftragsverarbeitungsvertrag" in text
    assert "ENTWURF" in text


def test_avv_pdf_contains_every_section_heading() -> None:
    pytest.importorskip("reportlab")
    content = get_compliance_content()

    text = _extract_text(AvvPdfExporter.export(content.avv))

    for section in content.avv.sections:
        assert section.heading in text


def test_avv_pdf_contains_paragraph_body_text_not_just_headings() -> None:
    """Regression test: a change to ``_render`` that drops the inner
    ``for paragraph in section.paragraphs`` loop (rendering only
    headings) would pass every other PDF test in this file — none of
    them assert on paragraph *body* text.
    """
    pytest.importorskip("reportlab")
    content = get_compliance_content()

    text = _extract_text(AvvPdfExporter.export(content.avv))

    for section in content.avv.sections:
        for paragraph in section.paragraphs:
            # reportlab may wrap/hyphenate very long paragraphs, so check
            # a stable prefix rather than the full string.
            assert paragraph[:40] in text, (
                f"paragraph body missing from AVV PDF: {paragraph[:40]!r}"
            )


def test_tom_exporter_produces_a_valid_pdf() -> None:
    pytest.importorskip("reportlab")
    content = get_compliance_content()

    pdf_bytes = TomPdfExporter.export(content.tom)

    assert pdf_bytes.startswith(b"%PDF")


def test_tom_pdf_contains_title_and_every_section_heading() -> None:
    pytest.importorskip("reportlab")
    content = get_compliance_content()

    text = _extract_text(TomPdfExporter.export(content.tom))

    assert "Technische und organisatorische Massnahmen" in text
    for section in content.tom.sections:
        assert section.heading in text


def test_tom_pdf_contains_paragraph_body_text_not_just_headings() -> None:
    pytest.importorskip("reportlab")
    content = get_compliance_content()

    text = _extract_text(TomPdfExporter.export(content.tom))

    for section in content.tom.sections:
        for paragraph in section.paragraphs:
            assert paragraph[:40] in text, (
                f"paragraph body missing from TOM PDF: {paragraph[:40]!r}"
            )


def test_pdf_export_escapes_xml_markup_in_content() -> None:
    """A heading/paragraph containing ``&``, ``<`` or ``>`` must not crash
    reportlab's XML parser. ``_pdf_safe`` escapes these before they hit
    ``Paragraph`` — see ``services.grade_export_service`` for the same
    regression covered against user-controlled input there. This module's
    content is currently developer-authored and static, but the exporter
    itself must stay safe against it regardless.
    """
    pytest.importorskip("reportlab")
    document = ComplianceDocument(
        title="AVV & TOM <Entwurf>",
        last_updated="Stand: <heute>",
        draft_notice="ENTWURF & unreviewed",
        sections=(
            ComplianceSection(
                heading="1. Vertraulichkeit & Integrität <Art. 32>",
                paragraphs=(
                    "Massnahmen A & B, C < D, E > F.",
                    "Weitere <strong>Auszeichnung</strong> & Sonderzeichen.",
                ),
            ),
        ),
    )

    pdf_bytes = AvvPdfExporter.export(document)

    assert pdf_bytes.startswith(b"%PDF")
