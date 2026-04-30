"""
Defense-in-depth tests for the document-processing pipeline.

These tests cover the two edge cases that currently cause silent failures:
1. `.doc` (legacy CFB/OLE2) — current implementation does
   `bytes.decode("utf-8", errors="ignore")` which yields garbage. The
   processor must reject input it cannot meaningfully extract.
2. Document processing that yields zero chunks must surface as an error,
   not silently produce a PROCESSED document without vectors.
"""

import io

import pytest
from docx import Document as DocxDocument

from services.document_processors.pymupdf_processor import PyMuPDFProcessor

DOC_MIME = "application/msword"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.fixture
def processor():
    return PyMuPDFProcessor(chunk_size=1000, chunk_overlap=200)


def _ole2_compound_file_bytes() -> bytes:
    """Minimal CFB/OLE2 header (no real content) — what a .doc looks like.

    A real .doc starts with the CFB magic number `D0 CF 11 E0 A1 B1 1A E1`.
    The current naive UTF-8 decoder produces garbage for such files; the
    new implementation must reject binary streams it cannot extract from.
    """
    header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    return header + b"\x00" * 1024


@pytest.mark.asyncio
async def test_doc_with_pure_binary_raises_clear_error(processor, tmp_path):
    """Garbage-only binary streams must NOT silently produce chunks."""
    path = tmp_path / "broken.doc"
    path.write_bytes(_ole2_compound_file_bytes())

    with pytest.raises(ValueError, match="(?i)no.*text|empty|legacy|leer"):
        await processor.process_document(
            document_id=1,
            file_path=str(path),
            filename="broken.doc",
            mime_type=DOC_MIME,
        )


@pytest.mark.asyncio
async def test_docx_with_only_images_yields_clear_error(processor, tmp_path):
    """A docx without any text content must raise, not silently return 0 chunks."""
    doc = DocxDocument()
    # Add a paragraph that contains only formatting / no text run
    p = doc.add_paragraph()
    p.style = doc.styles["Normal"]
    buf = io.BytesIO()
    doc.save(buf)
    path = tmp_path / "imageonly.docx"
    path.write_bytes(buf.getvalue())

    with pytest.raises(ValueError, match="(?i)no.*text|empty|leer"):
        await processor.process_document(
            document_id=2,
            file_path=str(path),
            filename="imageonly.docx",
            mime_type=DOCX_MIME,
        )


def test_pymupdf_processor_supports_documented_mime_types(processor):
    """Sanity: the processor advertises every mime type the API claims to support."""
    expected = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    }
    assert expected.issubset(processor.supported_types.keys())
