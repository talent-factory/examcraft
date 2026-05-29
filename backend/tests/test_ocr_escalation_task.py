"""Tests für die OCR-Eskalation: Placeholder-Vektorservice + Tasks (TF-360)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_placeholder_delete_document_chunks_raises_not_implemented():
    from services.vector_service_factory import VectorServicePlaceholder

    placeholder = VectorServicePlaceholder()
    with pytest.raises(NotImplementedError):
        await placeholder.delete_document_chunks(123)


def test_reprocess_document_ocr_deletes_old_vectors_and_sets_flags():
    from tasks import document_tasks

    document = MagicMock()
    document.id = 7
    document.processing_info = {"quality": {"ok": False, "reason": "scanned_low_text"}}

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document

    vector_service = MagicMock()
    vector_service.delete_document_chunks = AsyncMock(return_value=3)

    ocr_processor = MagicMock(name="ocr_processor")

    with_vectors_result = {"document_id": 7, "quality": {"ok": True, "reason": "ok"}}

    with (
        patch.object(document_tasks, "SessionLocal", return_value=db),
        patch.object(
            document_tasks,
            "get_vector_service",
            return_value=vector_service,
            create=True,
        ),
        patch.object(
            document_tasks,
            "create_ocr_processor",
            return_value=ocr_processor,
            create=True,
        ),
        patch.object(
            document_tasks.document_service,
            "process_document_with_vectors",
            AsyncMock(return_value=with_vectors_result),
        ) as mock_pdwv,
        patch.object(document_tasks.reprocess_document_ocr, "update_state"),
    ):
        result = document_tasks.reprocess_document_ocr(str(7), str(99))

    vector_service.delete_document_chunks.assert_awaited_once_with(7)
    assert mock_pdwv.call_args.kwargs["processor"] is ocr_processor
    assert document.processing_info["ocr_attempted"] is True
    assert document.processing_info["processed_with_ocr"] is True
    assert document.processing_info["escalation"] == "completed"
    assert result["success"] is True


def test_process_document_enqueues_ocr_when_quality_low_and_ocr_available():
    from tasks import document_tasks

    document = MagicMock()
    document.id = 5
    document.original_filename = "scan.pdf"
    document.status = MagicMock()
    document.status.value = "processed"
    document.has_vectors = True
    document.processing_info = {}

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document

    result = {"quality": {"ok": False, "reason": "scanned_low_text"}}

    with (
        patch.object(document_tasks, "SessionLocal", return_value=db),
        patch.object(document_tasks.process_document, "update_state"),
        patch.object(
            document_tasks.document_service,
            "process_document_with_vectors",
            AsyncMock(return_value=result),
        ),
        patch.object(document_tasks, "is_ocr_available", return_value=True),
        patch.object(
            document_tasks.reprocess_document_ocr, "apply_async"
        ) as mock_enqueue,
    ):
        document_tasks.process_document(str(5), str(99))

    mock_enqueue.assert_called_once_with(args=[str(5), str(99)])
    assert document.processing_info["escalation"] == "queued"


def test_process_document_marks_unavailable_when_ocr_missing():
    from tasks import document_tasks

    document = MagicMock()
    document.id = 6
    document.original_filename = "scan.pdf"
    document.status = MagicMock()
    document.status.value = "processed"
    document.has_vectors = True
    document.processing_info = {}

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document

    result = {"quality": {"ok": False, "reason": "scanned_low_text"}}

    with (
        patch.object(document_tasks, "SessionLocal", return_value=db),
        patch.object(document_tasks.process_document, "update_state"),
        patch.object(
            document_tasks.document_service,
            "process_document_with_vectors",
            AsyncMock(return_value=result),
        ),
        patch.object(document_tasks, "is_ocr_available", return_value=False),
        patch.object(
            document_tasks.reprocess_document_ocr, "apply_async"
        ) as mock_enqueue,
    ):
        document_tasks.process_document(str(6), str(99))

    mock_enqueue.assert_not_called()
    assert document.processing_info["escalation"] == "unavailable"


def test_process_document_no_escalation_when_quality_ok():
    from tasks import document_tasks

    document = MagicMock()
    document.id = 8
    document.original_filename = "clean.pdf"
    document.status = MagicMock()
    document.status.value = "processed"
    document.has_vectors = True
    document.processing_info = {}

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document

    result = {"quality": {"ok": True, "reason": "ok"}}

    with (
        patch.object(document_tasks, "SessionLocal", return_value=db),
        patch.object(document_tasks.process_document, "update_state"),
        patch.object(
            document_tasks.document_service,
            "process_document_with_vectors",
            AsyncMock(return_value=result),
        ),
        patch.object(document_tasks, "is_ocr_available", return_value=True),
        patch.object(
            document_tasks.reprocess_document_ocr, "apply_async"
        ) as mock_enqueue,
    ):
        document_tasks.process_document(str(8), str(99))

    mock_enqueue.assert_not_called()
    assert document.processing_info.get("escalation") == "not_needed"


def test_reprocess_document_ocr_exhausted_when_quality_still_poor():
    from tasks import document_tasks

    document = MagicMock()
    document.id = 11
    document.processing_info = {}

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document

    vector_service = MagicMock()
    vector_service.delete_document_chunks = AsyncMock(return_value=2)

    # OCR-Lauf bringt immer noch schlechte Qualität -> "exhausted".
    result = {"document_id": 11, "quality": {"ok": False, "reason": "scanned_low_text"}}

    with (
        patch.object(document_tasks, "SessionLocal", return_value=db),
        patch.object(document_tasks.reprocess_document_ocr, "update_state"),
        patch.object(document_tasks, "get_vector_service", return_value=vector_service),
        patch.object(document_tasks, "create_ocr_processor", return_value=MagicMock()),
        patch.object(
            document_tasks.document_service,
            "process_document_with_vectors",
            AsyncMock(return_value=result),
        ),
    ):
        out = document_tasks.reprocess_document_ocr(str(11), str(99))

    assert document.processing_info["escalation"] == "exhausted"
    assert document.processing_info["ocr_attempted"] is True
    assert document.processing_info["processed_with_ocr"] is True
    assert out["escalation"] == "exhausted"


def test_reprocess_document_ocr_error_path_sets_failed():
    from tasks import document_tasks
    from models.document import DocumentStatus

    document = MagicMock()
    document.id = 12
    document.processing_info = {}

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document

    vector_service = MagicMock()
    vector_service.delete_document_chunks = AsyncMock(return_value=0)

    with (
        patch.object(document_tasks, "SessionLocal", return_value=db),
        patch.object(document_tasks.reprocess_document_ocr, "update_state"),
        patch.object(document_tasks, "get_vector_service", return_value=vector_service),
        patch.object(document_tasks, "create_ocr_processor", return_value=MagicMock()),
        patch.object(
            document_tasks.document_service,
            "process_document_with_vectors",
            AsyncMock(side_effect=RuntimeError("OCR boom")),
        ),
    ):
        with pytest.raises(RuntimeError):
            document_tasks.reprocess_document_ocr(str(12), str(99))

    assert document.processing_info["ocr_attempted"] is True
    assert document.processing_info["escalation"] == "failed"
    assert document.status == DocumentStatus.ERROR


def test_process_document_loop_guard_skips_when_already_attempted():
    from tasks import document_tasks

    document = MagicMock()
    document.id = 13
    document.original_filename = "scan.pdf"
    document.status = MagicMock()
    document.status.value = "processed"
    document.has_vectors = True
    document.processing_info = {"ocr_attempted": True, "escalation": "exhausted"}

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document

    result = {"quality": {"ok": False, "reason": "scanned_low_text"}}

    with (
        patch.object(document_tasks, "SessionLocal", return_value=db),
        patch.object(document_tasks.process_document, "update_state"),
        patch.object(
            document_tasks.document_service,
            "process_document_with_vectors",
            AsyncMock(return_value=result),
        ),
        patch.object(document_tasks, "is_ocr_available", return_value=True),
        patch.object(
            document_tasks.reprocess_document_ocr, "apply_async"
        ) as mock_enqueue,
    ):
        document_tasks.process_document(str(13), str(99))

    mock_enqueue.assert_not_called()
    assert document.processing_info["escalation"] == "exhausted"


def test_process_document_no_verdict_when_quality_missing():
    from tasks import document_tasks

    document = MagicMock()
    document.id = 14
    document.original_filename = "x.pdf"
    document.status = MagicMock()
    document.status.value = "error"
    document.has_vectors = False
    document.processing_info = {}

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = document

    # Vektorisierung fehlgeschlagen: Result-Dict ohne 'quality'.
    result = {"document_id": 14, "vector_embeddings": {"error": "qdrant down"}}

    with (
        patch.object(document_tasks, "SessionLocal", return_value=db),
        patch.object(document_tasks.process_document, "update_state"),
        patch.object(
            document_tasks.document_service,
            "process_document_with_vectors",
            AsyncMock(return_value=result),
        ),
        patch.object(document_tasks, "is_ocr_available", return_value=True),
        patch.object(
            document_tasks.reprocess_document_ocr, "apply_async"
        ) as mock_enqueue,
    ):
        document_tasks.process_document(str(14), str(99))

    mock_enqueue.assert_not_called()
    assert document.processing_info["escalation"] == "no_verdict"
