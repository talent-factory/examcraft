"""
Tests für den progress_callback-Parameter in generate_rag_exam.
Testet die Callback-Integration ohne echten Claude API-Aufruf.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_generate_rag_exam_accepts_progress_callback():
    """generate_rag_exam akzeptiert progress_callback ohne Fehler"""
    # Importiere nur wenn Premium verfügbar
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    import inspect

    sig = inspect.signature(RAGService.generate_rag_exam)
    assert "progress_callback" in sig.parameters


@pytest.mark.asyncio
async def test_generate_rag_exam_calls_callback_after_context():
    """Callback wird nach dem Context-Laden aufgerufen (Step 1)"""
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    request = RAGExamRequest(topic="Test", question_count=2)
    callback_calls = []

    def mock_callback(current, total, message):
        callback_calls.append((current, total, message))

    service = RAGService.__new__(RAGService)

    mock_context = MagicMock()
    mock_context.retrieved_chunks = [MagicMock()]
    mock_context.query = "Test"
    mock_context.total_similarity_score = 0.9
    mock_context.source_documents = []
    mock_context.context_length = 100

    mock_question = MagicMock()
    mock_question.model_dump = MagicMock(return_value={})

    service.retrieve_context = AsyncMock(return_value=mock_context)
    service.generate_question = AsyncMock(return_value=mock_question)
    service._calculate_quality_metrics = MagicMock(return_value={})

    await service.generate_rag_exam(request, progress_callback=mock_callback)

    # Step 1 = Context geladen (current=1)
    assert any(call[0] == 1 for call in callback_calls), (
        f"Expected callback with current=1, got: {callback_calls}"
    )


@pytest.mark.asyncio
async def test_generate_rag_exam_calls_callback_per_question():
    """Callback wird nach jeder generierten Frage aufgerufen"""
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    question_count = 3
    request = RAGExamRequest(topic="Test", question_count=question_count)
    callback_calls = []

    def mock_callback(current, total, message):
        callback_calls.append((current, total, message))

    service = RAGService.__new__(RAGService)

    mock_context = MagicMock()
    mock_context.retrieved_chunks = [MagicMock(), MagicMock(), MagicMock()]
    mock_context.query = "Test"
    mock_context.total_similarity_score = 0.9
    mock_context.source_documents = []
    mock_context.context_length = 300

    mock_question = MagicMock()
    mock_question.model_dump = MagicMock(return_value={})

    service.retrieve_context = AsyncMock(return_value=mock_context)
    service.generate_question = AsyncMock(return_value=mock_question)
    service._calculate_quality_metrics = MagicMock(return_value={})

    await service.generate_rag_exam(request, progress_callback=mock_callback)

    # 1 context call + question_count question calls
    assert len(callback_calls) == question_count + 1, (
        f"Expected {question_count + 1} callbacks, got {len(callback_calls)}"
    )
    # Last question call has current = question_count + 1
    question_calls = [c for c in callback_calls if c[0] >= 2]
    assert len(question_calls) == question_count


@pytest.mark.asyncio
async def test_generate_rag_exam_callback_messages_are_german():
    """Callback-Messages sind auf Deutsch"""
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    request = RAGExamRequest(topic="Test", question_count=2)
    messages = []

    def mock_callback(current, total, message):
        messages.append(message)

    service = RAGService.__new__(RAGService)

    mock_context = MagicMock()
    mock_context.retrieved_chunks = [MagicMock(), MagicMock()]
    mock_context.query = "Test"
    mock_context.total_similarity_score = 0.9
    mock_context.source_documents = []
    mock_context.context_length = 200

    mock_question = MagicMock()
    service.retrieve_context = AsyncMock(return_value=mock_context)
    service.generate_question = AsyncMock(return_value=mock_question)
    service._calculate_quality_metrics = MagicMock(return_value={})

    await service.generate_rag_exam(request, progress_callback=mock_callback)

    assert any("Context" in m or "geladen" in m.lower() for m in messages), (
        f"Expected German context message, got: {messages}"
    )
    assert any("Frage" in m for m in messages), (
        f"Expected German question message, got: {messages}"
    )


@pytest.mark.asyncio
async def test_generate_rag_exam_works_without_callback():
    """generate_rag_exam funktioniert ohne Callback (None)"""
    pytest.importorskip("premium.services.rag_service")
    from premium.services.rag_service import RAGService
    from services.rag_service import RAGExamRequest

    request = RAGExamRequest(topic="Test", question_count=1)
    service = RAGService.__new__(RAGService)

    mock_context = MagicMock()
    mock_context.retrieved_chunks = [MagicMock()]
    mock_context.query = "Test"
    mock_context.total_similarity_score = 0.9
    mock_context.source_documents = []
    mock_context.context_length = 100

    mock_question = MagicMock()
    service.retrieve_context = AsyncMock(return_value=mock_context)
    service.generate_question = AsyncMock(return_value=mock_question)
    service._calculate_quality_metrics = MagicMock(return_value={})

    # Sollte kein Fehler werfen
    result = await service.generate_rag_exam(request, progress_callback=None)
    assert result is not None
