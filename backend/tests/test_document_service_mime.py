"""
Tests for the MIME-type detection fallback in DocumentService.

`magic.from_buffer` (used at upload time) is known to return `application/zip`
for `.docx` on some libmagic versions because OOXML files are ZIP archives
under the hood. Without a fallback to the file extension this poisons the
downstream processing pipeline (the document is stored with mime_type=zip,
which the processor rejects with "Unsupported MIME type").
"""

import io

import pytest
from docx import Document as DocxDocument

from services.document_service import DocumentService


@pytest.fixture
def service():
    return DocumentService()


def _docx_bytes() -> bytes:
    doc = DocxDocument()
    doc.add_paragraph("hello")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_buffer_detection_falls_back_to_extension_for_docx(service, monkeypatch):
    """When libmagic returns generic `application/zip` we must still recognise .docx."""
    import services.document_service as ds_mod

    monkeypatch.setattr(
        ds_mod.magic, "from_buffer", lambda *_args, **_kw: "application/zip"
    )
    detected = service._detect_mime_type_from_bytes(
        _docx_bytes(), "Pareto-Prinzip.docx"
    )
    assert detected == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_buffer_detection_falls_back_to_extension_for_doc(service, monkeypatch):
    """Legacy .doc commonly reports as application/x-ole-storage or octet-stream."""
    import services.document_service as ds_mod

    monkeypatch.setattr(
        ds_mod.magic, "from_buffer", lambda *_args, **_kw: "application/x-ole-storage"
    )
    detected = service._detect_mime_type_from_bytes(
        b"\xd0\xcf" + b"\x00" * 100, "old.doc"
    )
    assert detected == "application/msword"


def test_buffer_detection_keeps_correct_mime_when_already_supported(
    service, monkeypatch
):
    """Don't override a correct MIME type just because we have a fallback."""
    import services.document_service as ds_mod

    correct = "application/pdf"
    monkeypatch.setattr(ds_mod.magic, "from_buffer", lambda *_args, **_kw: correct)
    assert service._detect_mime_type_from_bytes(b"%PDF-1.4", "x.pdf") == correct


def test_buffer_detection_falls_back_when_magic_raises(service, monkeypatch):
    """Existing exception fallback must still work."""
    import services.document_service as ds_mod

    def boom(*_a, **_k):
        raise RuntimeError("libmagic broken")

    monkeypatch.setattr(ds_mod.magic, "from_buffer", boom)
    assert service._detect_mime_type_from_bytes(b"any", "doc.txt") == "text/plain"


def test_md_extension_overrides_text_plain_from_libmagic(service, monkeypatch):
    """libmagic returns text/plain for .md files; we must classify as text/markdown.

    Markdown is syntactically plain text, so libmagic's content sniffing returns
    `text/plain`. The previous logic accepted that because text/plain is in
    supported_formats — but then the file was processed via _process_text and
    the markdown-specific path (heading extraction, syntax stripping) was
    silently bypassed.
    """
    import services.document_service as ds_mod

    monkeypatch.setattr(ds_mod.magic, "from_buffer", lambda *_a, **_kw: "text/plain")
    md_content = b"# Heading\n\nSome **markdown** content.\n"
    detected = service._detect_mime_type_from_bytes(md_content, "notes.md")
    assert detected == "text/markdown"


def test_txt_extension_kept_as_text_plain(service, monkeypatch):
    """Regression: .txt files must not be reclassified to text/markdown."""
    import services.document_service as ds_mod

    monkeypatch.setattr(ds_mod.magic, "from_buffer", lambda *_a, **_kw: "text/plain")
    assert (
        service._detect_mime_type_from_bytes(b"plain text\n", "notes.txt")
        == "text/plain"
    )


def test_pdf_extension_kept_when_libmagic_agrees(service, monkeypatch):
    """Regression: .pdf must remain application/pdf when libmagic agrees."""
    import services.document_service as ds_mod

    monkeypatch.setattr(
        ds_mod.magic, "from_buffer", lambda *_a, **_kw: "application/pdf"
    )
    assert (
        service._detect_mime_type_from_bytes(b"%PDF-1.4", "doc.pdf")
        == "application/pdf"
    )
