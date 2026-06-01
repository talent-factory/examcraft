"""
Tests für .txt- und .md-Extraktion im PyMuPDFProcessor.

Hintergrund: Die DOCX-Vektorisierungs-Bugfix-Story (TF-331) deckte die Frage auf,
ob die anderen unterstützten Textformate (.txt und .md) ebenfalls vollständig
durch die Pipeline laufen. Konkret:

* `.md` wird von `libmagic` als `text/plain` klassifiziert — wir müssen die
  Datei-Endung priorisieren, damit der Markdown-spezifische Code-Pfad
  (Heading-Extraktion, Syntax-Stripping) erreicht wird.
* `_process_markdown` muss — analog zu `_process_text` — einen Latin-1-Fallback
  bieten, um nicht-UTF-8-Markdown-Dateien nicht hart fallen zu lassen.
* End-to-End: Beide Formate müssen non-leere Chunks plus Metadaten produzieren.
"""

import fitz
import pytest

from services.document_errors import OCR_ENGINE_FAILURE, DocumentProcessingError
from services.document_processors.pymupdf_processor import PyMuPDFProcessor


@pytest.fixture
def processor():
    return PyMuPDFProcessor(chunk_size=1000, chunk_overlap=200)


@pytest.mark.asyncio
async def test_text_file_produces_chunks(processor, tmp_path):
    """A plain .txt should be processed into at least one chunk."""
    txt_file = tmp_path / "notes.txt"
    body = "Dies ist ein Beispieldokument.\n" * 20
    txt_file.write_text(body, encoding="utf-8")

    result = await processor.process_document(
        document_id=1,
        file_path=str(txt_file),
        filename="notes.txt",
        mime_type="text/plain",
    )

    assert result.total_chunks >= 1
    full_text = " ".join(c.content for c in result.chunks)
    assert "Beispieldokument" in full_text
    assert result.metadata["title"] == "notes"
    assert result.metadata["encoding"] == "utf-8"


@pytest.mark.asyncio
async def test_text_file_latin1_fallback(processor, tmp_path):
    """Latin-1 encoded .txt must not crash and must extract correctly."""
    txt_file = tmp_path / "umlaute.txt"
    txt_file.write_bytes("Über Ärger und Öl".encode("latin-1"))

    result = await processor.process_document(
        document_id=2,
        file_path=str(txt_file),
        filename="umlaute.txt",
        mime_type="text/plain",
    )

    full_text = " ".join(c.content for c in result.chunks)
    assert "Über" in full_text
    assert result.metadata["encoding"] == "latin-1"


@pytest.mark.asyncio
async def test_markdown_file_extracts_headings_into_metadata(processor, tmp_path):
    """Markdown processing must populate metadata.sections from `#` headings."""
    md_file = tmp_path / "guide.md"
    md_file.write_text(
        "# Hauptkapitel\n\n"
        "Einleitungstext.\n\n"
        "## Unterabschnitt A\n\n"
        "Inhalt A.\n\n"
        "## Unterabschnitt B\n\n"
        "Inhalt B.\n",
        encoding="utf-8",
    )

    result = await processor.process_document(
        document_id=3,
        file_path=str(md_file),
        filename="guide.md",
        mime_type="text/markdown",
    )

    assert result.total_chunks >= 1
    sections = result.metadata.get("sections", [])
    assert "Hauptkapitel" in sections
    assert "Unterabschnitt A" in sections
    assert "Unterabschnitt B" in sections
    assert result.metadata["format"] == "Markdown"


@pytest.mark.asyncio
async def test_markdown_strips_syntax_from_chunk_text(processor, tmp_path):
    """Markdown formatting characters should not leak into vectorised chunks.

    Heading hashes and bold/italic markers should be stripped — otherwise
    embeddings carry irrelevant punctuation noise. Also pins down the
    routing: format must be "Markdown" (i.e. _process_markdown was called,
    not _process_text), and encoding must be UTF-8.
    """
    md_file = tmp_path / "syntax.md"
    md_file.write_text(
        "# Title\n\nSome **bold** and *italic* text.\n",
        encoding="utf-8",
    )

    result = await processor.process_document(
        document_id=4,
        file_path=str(md_file),
        filename="syntax.md",
        mime_type="text/markdown",
    )

    full_text = " ".join(c.content for c in result.chunks)
    assert "Title" in full_text
    assert "bold" in full_text
    assert "italic" in full_text
    # Heading hashes and emphasis markers must be stripped
    assert "# Title" not in full_text
    assert "**bold**" not in full_text
    # Routing assertions: must have gone through _process_markdown
    assert result.metadata["format"] == "Markdown"
    assert result.metadata["encoding"] == "utf-8"


@pytest.mark.asyncio
async def test_markdown_latin1_fallback(processor, tmp_path):
    """Latin-1 encoded .md must not crash on UnicodeDecodeError."""
    md_file = tmp_path / "umlaute.md"
    md_file.write_bytes("# Überschrift\n\nÄÖÜ ßeispieltext.\n".encode("latin-1"))

    result = await processor.process_document(
        document_id=5,
        file_path=str(md_file),
        filename="umlaute.md",
        mime_type="text/markdown",
    )

    full_text = " ".join(c.content for c in result.chunks)
    assert "Überschrift" in full_text
    assert "ßeispieltext" in full_text


@pytest.mark.asyncio
async def test_empty_text_file_yields_zero_chunks(processor, tmp_path):
    """Whitespace-only .txt produces 0 chunks at processor level.

    The processor returns an empty ProcessedDocument; the upstream
    defense-in-depth in `DocumentService.process_document_content`
    converts that into a document with status=ERROR. The end-to-end
    behaviour is asserted in `test_empty_file_marks_document_as_error`.
    """
    txt_file = tmp_path / "empty.txt"
    txt_file.write_text("   \n\n  \n", encoding="utf-8")

    result = await processor.process_document(
        document_id=6,
        file_path=str(txt_file),
        filename="empty.txt",
        mime_type="text/plain",
    )
    assert result.total_chunks == 0


@pytest.mark.asyncio
async def test_empty_markdown_file_yields_zero_chunks(processor, tmp_path):
    """Empty .md (only headings stripped) produces 0 chunks for upstream guard."""
    md_file = tmp_path / "empty.md"
    md_file.write_text("", encoding="utf-8")

    result = await processor.process_document(
        document_id=7,
        file_path=str(md_file),
        filename="empty.md",
        mime_type="text/markdown",
    )
    assert result.total_chunks == 0


@pytest.mark.asyncio
async def test_binary_renamed_as_md_is_rejected(processor, tmp_path):
    """A binary file renamed `.md` must not silently vectorize as mojibake.

    Latin-1 decodes any byte sequence — without the printable-character
    check this would silently produce nonsense embeddings.
    """
    md_file = tmp_path / "fake.md"
    # All 256 bytes repeated → ~50% control chars → fails printable ratio.
    md_file.write_bytes(bytes(range(256)) * 4)

    with pytest.raises(ValueError, match="(?i)not.*text|binary"):
        await processor.process_document(
            document_id=8,
            file_path=str(md_file),
            filename="fake.md",
            mime_type="text/markdown",
        )


@pytest.mark.parametrize(
    "filename,extension_content,mime",
    [
        ("empty.txt", "   \n\n   \n", "text/plain"),
        ("empty.md", "", "text/markdown"),
    ],
)
@pytest.mark.asyncio
async def test_empty_file_marks_document_as_error(
    tmp_path, filename, extension_content, mime
):
    """Defense-in-depth E2E: empty .txt/.md → document.status == ERROR.

    The processor returning 0 chunks is only half the contract; the
    user-facing guarantee is that ``process_document_content`` flips
    the document to ERROR with an actionable error message stored in
    metadata. This test pins the full pipeline.
    """
    from unittest.mock import MagicMock

    from models.document import Document, DocumentStatus
    from services.document_service import DocumentService

    file_path = tmp_path / filename
    file_path.write_text(extension_content, encoding="utf-8")

    document = Document(
        filename=filename,
        original_filename=filename,
        file_path=str(file_path),
        file_size=file_path.stat().st_size,
        mime_type=mime,
        status=DocumentStatus.UPLOADED,
        user_id=1,
        vector_collection="doc_test",
    )

    db = MagicMock()
    service = DocumentService()
    # Bypass the DB lookup — return our in-memory document for both calls
    # (the success path AND the error-handler path both call get_document_by_id).
    service.get_document_by_id = MagicMock(return_value=document)

    result = await service.process_document_content(document_id=42, db=db)

    assert result is None
    assert document.status == DocumentStatus.ERROR
    assert document.doc_metadata is not None
    assert "error" in document.doc_metadata
    assert "no extractable text" in document.doc_metadata["error"].lower()


def test_pymupdf_processor_ocr_disabled_by_default():
    from services.document_processors.pymupdf_processor import PyMuPDFProcessor

    proc = PyMuPDFProcessor()
    assert proc.enable_ocr is False


def test_pymupdf_processor_ocr_flag_enabled():
    from services.document_processors.pymupdf_processor import PyMuPDFProcessor

    proc = PyMuPDFProcessor(enable_ocr=True)
    assert proc.enable_ocr is True
    assert proc.ocr_language == "deu+eng"


def test_is_ocr_available_requires_env_binary_and_traineddata(monkeypatch):
    from services.document_processors import processor_factory

    # Voll verfügbar: Env gesetzt + Binary im PATH + Sprachpaket vorhanden.
    monkeypatch.setenv("TESSDATA_PREFIX", "/fake/tessdata")
    monkeypatch.setattr(
        processor_factory.shutil, "which", lambda _: "/usr/bin/tesseract"
    )
    monkeypatch.setattr(processor_factory.os.path, "isfile", lambda _: True)
    assert processor_factory.is_ocr_available() is True

    # Env fehlt -> nicht verfügbar.
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    assert processor_factory.is_ocr_available() is False

    # Env gesetzt, aber Tesseract-Binary fehlt -> nicht verfügbar.
    monkeypatch.setenv("TESSDATA_PREFIX", "/fake/tessdata")
    monkeypatch.setattr(processor_factory.shutil, "which", lambda _: None)
    assert processor_factory.is_ocr_available() is False

    # Binary da, aber traineddata fehlt -> nicht verfügbar.
    monkeypatch.setattr(
        processor_factory.shutil, "which", lambda _: "/usr/bin/tesseract"
    )
    monkeypatch.setattr(processor_factory.os.path, "isfile", lambda _: False)
    assert processor_factory.is_ocr_available() is False


def test_create_ocr_processor_enables_ocr():
    from services.document_processors.pymupdf_processor import PyMuPDFProcessor
    from services.document_processors.processor_factory import create_ocr_processor

    proc = create_ocr_processor()
    assert isinstance(proc, PyMuPDFProcessor)
    assert proc.enable_ocr is True


def _make_pdf(tmp_path, n_pages: int = 2, name: str = "scan.pdf") -> str:
    """Erzeuge ein mehrseitiges PDF (Inhalt egal — OCR-Aufruf wird gemockt)."""
    doc = fitz.open()
    for _ in range(n_pages):
        doc.new_page()
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.mark.asyncio
async def test_pdf_ocr_page_failure_counted_not_fatal(tmp_path, monkeypatch):
    """Nicht-RuntimeError-Abbruch auf einer OCR-Seite: zählen, nicht fatal."""
    processor = PyMuPDFProcessor(enable_ocr=True)
    path = _make_pdf(tmp_path, n_pages=2)

    def _fake_ocr(page, page_num, filename):
        if page_num == 1:
            raise ValueError("malformed textpage / OOM-killed subprocess")
        return f"SEITENTEXT {page_num}"

    monkeypatch.setattr(processor, "_ocr_pdf_page", _fake_ocr)

    result = await processor.process_document(
        document_id=1, file_path=path, filename="scan.pdf", mime_type="application/pdf"
    )

    full_text = " ".join(c.content for c in result.chunks)
    assert "SEITENTEXT 0" in full_text  # überlebende Seite erhalten
    assert result.metadata["ocr_pages_attempted"] == 2
    assert result.metadata["ocr_pages_discarded"] == 1


@pytest.mark.asyncio
async def test_pdf_ocr_engine_failure_still_fatal(tmp_path, monkeypatch):
    """RuntimeError-Pfad bleibt fatal: DocumentProcessingError(OCR_ENGINE_FAILURE)."""
    processor = PyMuPDFProcessor(enable_ocr=True)
    path = _make_pdf(tmp_path, n_pages=2)

    def _boom(page, page_num, filename):
        raise DocumentProcessingError(
            OCR_ENGINE_FAILURE, "Tesseract kaputt", filename=filename
        )

    monkeypatch.setattr(processor, "_ocr_pdf_page", _boom)

    with pytest.raises(DocumentProcessingError) as exc_info:
        await processor.process_document(
            document_id=2,
            file_path=path,
            filename="scan.pdf",
            mime_type="application/pdf",
        )
    assert exc_info.value.code == OCR_ENGINE_FAILURE


@pytest.mark.asyncio
async def test_ocr_pdf_page_converts_runtimeerror_to_engine_failure():
    """Der Helper wandelt RuntimeError aus get_textpage_ocr in OCR_ENGINE_FAILURE."""
    processor = PyMuPDFProcessor(enable_ocr=True)

    class _FakePage:
        def get_textpage_ocr(self, **kwargs):
            raise RuntimeError("tesseract not found")

    with pytest.raises(DocumentProcessingError) as exc_info:
        processor._ocr_pdf_page(_FakePage(), page_num=0, filename="x.pdf")
    assert exc_info.value.code == OCR_ENGINE_FAILURE


@pytest.mark.asyncio
async def test_ocr_pdf_page_returns_text_on_success():
    """Erfolgsfall: Helper liefert den OCR-Text der Textpage zurück."""
    processor = PyMuPDFProcessor(enable_ocr=True)

    sentinel_tp = object()

    class _FakePage:
        def get_textpage_ocr(self, **kwargs):
            return sentinel_tp

        def get_text(self, mode, textpage=None):
            assert textpage is sentinel_tp
            return "OK TEXT"

    assert processor._ocr_pdf_page(_FakePage(), 0, "x.pdf") == "OK TEXT"


@pytest.mark.asyncio
async def test_pdf_no_discard_metadata_when_ocr_disabled(tmp_path):
    """Erstlauf ohne OCR setzt keine Discard-Metadaten."""
    processor = PyMuPDFProcessor(enable_ocr=False)
    path = _make_pdf(tmp_path, n_pages=1)
    result = await processor.process_document(
        document_id=3, file_path=path, filename="scan.pdf", mime_type="application/pdf"
    )
    assert "ocr_pages_attempted" not in result.metadata
    assert "ocr_pages_discarded" not in result.metadata
