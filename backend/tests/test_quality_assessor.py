"""Tests für den deterministischen QualityAssessor (TF-360)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.docling_service import DocumentChunk, ProcessedDocument
from services.quality_assessor import (
    DocumentQualityStats,
    QualityVerdict,
    assess_quality,
    compute_quality_stats,
)


def _stats(**overrides) -> DocumentQualityStats:
    base = dict(
        page_count=10,
        total_chars=50_000,
        chunk_count=12,
        garbage_char_ratio=0.0,
        file_size=500_000,
    )
    base.update(overrides)
    return DocumentQualityStats(**base)


def test_clean_document_passes():
    verdict = assess_quality(_stats())
    assert isinstance(verdict, QualityVerdict)
    assert verdict.ok is True
    assert verdict.reason == "ok"


def test_scanned_pdf_low_text_per_page_fails():
    verdict = assess_quality(_stats(page_count=3, total_chars=12, chunk_count=1))
    assert verdict.ok is False
    assert verdict.reason == "scanned_low_text"
    assert verdict.signals["chars_per_page"] < 100


def test_single_chunk_large_file_fails():
    verdict = assess_quality(
        _stats(page_count=4, total_chars=600, chunk_count=1, file_size=1_048_576)
    )
    assert verdict.ok is False
    assert verdict.reason == "single_chunk_large_file"


def test_garbage_extraction_fails():
    verdict = assess_quality(_stats(garbage_char_ratio=0.5))
    assert verdict.ok is False
    assert verdict.reason == "garbage_extraction"


def test_compute_quality_stats_from_processed_doc():
    chunks = [DocumentChunk(content="Hallo Welt", chunk_index=0)]
    doc = ProcessedDocument(
        document_id=1,
        filename="x.pdf",
        mime_type="application/pdf",
        total_pages=2,
        total_chunks=1,
        chunks=chunks,
        metadata={},
        processing_time=0.1,
    )
    stats = compute_quality_stats(doc, file_size=2048)
    assert stats.page_count == 2
    assert stats.chunk_count == 1
    assert stats.total_chars == len("Hallo Welt")
    assert stats.file_size == 2048
    assert stats.garbage_char_ratio == 0.0


@pytest.mark.asyncio
async def test_process_with_vectors_persists_quality_verdict():
    """process_document_with_vectors schreibt das Verdict nach processing_info
    und gibt es im Result-Dict zurück."""
    from services.docling_service import DocumentChunk, ProcessedDocument
    from services.document_service import document_service

    processed = ProcessedDocument(
        document_id=42,
        filename="scan.pdf",
        mime_type="application/pdf",
        total_pages=3,
        total_chunks=1,
        chunks=[DocumentChunk(content="x", chunk_index=0)],
        metadata={"processing_method": "pymupdf"},
        processing_time=0.1,
    )

    document = MagicMock()
    document.id = 42
    document.file_size = 1_048_576
    document.doc_metadata = {}
    document.processing_info = None

    embedding_stats = MagicMock(
        model_name="m", embedding_dimension=384, total_chunks=1, processing_time=0.1
    )
    vector_service = MagicMock()
    vector_service.add_document_chunks = AsyncMock(return_value=embedding_stats)

    with (
        patch.object(
            document_service,
            "process_document_content",
            AsyncMock(return_value=processed),
        ),
        patch.object(document_service, "get_document_by_id", return_value=document),
        patch(
            "services.document_service.get_vector_service", return_value=vector_service
        ),
    ):
        db = MagicMock()
        result = await document_service.process_document_with_vectors(42, db)

    assert result["quality"]["ok"] is False
    assert result["quality"]["reason"] == "scanned_low_text"
    assert document.processing_info["quality"]["reason"] == "scanned_low_text"
    assert document.processing_info["processor_chain"] == ["pymupdf"]
    assert document.processing_info["processed_with_ocr"] is False


def test_chars_per_page_threshold_boundary():
    # Genau auf der Schwelle (100) -> ok (Bedingung ist < 100).
    assert (
        assess_quality(_stats(page_count=1, total_chars=100, chunk_count=5)).reason
        == "ok"
    )
    # Knapp darunter -> scanned_low_text.
    assert (
        assess_quality(_stats(page_count=1, total_chars=99, chunk_count=5)).reason
        == "scanned_low_text"
    )


def test_garbage_ratio_threshold_boundary():
    assert assess_quality(_stats(garbage_char_ratio=0.30)).reason == "ok"
    assert (
        assess_quality(_stats(garbage_char_ratio=0.31)).reason == "garbage_extraction"
    )


def test_single_chunk_requires_more_than_min_pages():
    # page_count == 2 (LOW_CHUNK_MIN_PAGES): Bedingung page_count > 2 ist False -> ok.
    assert (
        assess_quality(
            _stats(page_count=2, total_chars=5000, chunk_count=1, file_size=1_048_576)
        ).reason
        == "ok"
    )
    # page_count == 3 -> > 2 -> single_chunk_large_file.
    assert (
        assess_quality(
            _stats(page_count=3, total_chars=5000, chunk_count=1, file_size=1_048_576)
        ).reason
        == "single_chunk_large_file"
    )


def test_scanned_low_text_takes_precedence_over_single_chunk():
    # Beide Bedingungen erfüllt: wenig Text/Seite UND 1 Chunk grosse Datei.
    verdict = assess_quality(
        _stats(page_count=4, total_chars=40, chunk_count=1, file_size=1_048_576)
    )
    assert verdict.reason == "scanned_low_text"


def test_document_quality_stats_rejects_out_of_range_ratio():
    with pytest.raises(ValueError):
        DocumentQualityStats(
            page_count=1,
            total_chars=1,
            chunk_count=1,
            garbage_char_ratio=1.5,
            file_size=1,
        )
