"""
Tests für Chat-zu-Dokument-Vektorisierung.

Bisheriges Verhalten: Convert-Chat-to-Document erstellte ein DBDocument mit
virtuellem file_path (/tmp/chat_exports/...) und status=PROCESSED, has_vectors=False.
Der Chat-Export landete also NICHT im Vector-Index — Re-Upload-Workaround nötig.

Neues Verhalten: Convert-Chat-to-Document soll wie ein normaler Document-Upload
eine echte Datei schreiben und den Celery-Vectorization-Task dispatchen.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
from datetime import datetime

# Test-Suite wird übersprungen wenn das Premium-Package nicht installiert ist
# (z. B. im Core-only CI-Job). Pattern analog test_question_generation_progress_callback.
pytest.importorskip("premium.api.v1.chat")
pytest.importorskip("premium.models.chat_db")


@pytest.fixture(scope="module")
def _ensure_chat_tables(test_engine):
    """
    Stellt sicher dass Premium-Chat-Tabellen in der Test-DB existieren.

    conftest.py importiert nur Core-Models — premium.models.chat_db wird daher
    nicht automatisch in Base.metadata registriert. Diese Fixture importiert die
    Premium-Models und legt fehlende Tabellen nach.
    """
    import premium.models.chat_db  # noqa: F401  # registriert Tabellen
    from database import Base

    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.mark.asyncio
async def test_convert_chat_to_document_dispatches_celery_vectorization(
    test_db, _ensure_chat_tables
):
    """
    Convert-chat-to-document soll Celery-Task dispatchen + Status QUEUED setzen,
    damit der Chat-Export anschliessend vektorisiert wird (analog Upload).
    """
    from premium.api.v1.chat import convert_chat_to_document
    from premium.models.chat_db import (
        ChatSession as DBChatSession,
        ChatMessage as DBChatMessage,
    )
    from models.document import Document as DBDocument, DocumentStatus
    from models.auth import Institution, User, UserStatus

    # --- Setup Institution + User (FK constraints) ---
    institution = Institution(
        name="Vec Test Uni",
        slug="vec-test-uni",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(institution)
    test_db.commit()

    user = User(
        email=f"vec-test-{uuid4().hex[:8]}@example.com",
        first_name="Vec",
        last_name="Test",
        password_hash="x",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # --- Setup: Chat-Session + Messages ---
    session_id = uuid4()
    session = DBChatSession(
        id=session_id,
        title="Pareto-Prinzip",
        document_ids=[],
        created_at=datetime.utcnow(),
        user_id=user.id,
    )
    test_db.add(session)
    test_db.add_all(
        [
            DBChatMessage(
                session_id=session_id,
                role="user",
                content="Was ist das Pareto-Prinzip?",
            ),
            DBChatMessage(
                session_id=session_id,
                role="assistant",
                content="Das Pareto-Prinzip besagt: 80 % der Wirkung kommt von 20 % der Ursachen.",
            ),
        ]
    )
    test_db.commit()

    # --- Mocks: document_service.upload_document und Celery ---
    # upload_document() schreibt sonst echte Datei nach storage/uploads — mocken.
    fake_document = DBDocument(
        filename="chat_export_xyz.md",
        original_filename="chat_export_xyz.md",
        file_path="storage/uploads/chat_export_xyz.md",
        file_size=200,
        mime_type="text/markdown",
        status=DocumentStatus.UPLOADED,
        user_id=user.id,
    )
    test_db.add(fake_document)
    test_db.commit()
    test_db.refresh(fake_document)

    mock_task = MagicMock()
    mock_task.id = "celery-task-id-abc"

    with (
        patch("premium.api.v1.chat.document_service") as mock_doc_service,
        patch("premium.api.v1.chat.celery_process_document") as mock_celery,
    ):
        mock_doc_service.upload_document = AsyncMock(return_value=fake_document)
        mock_celery.apply_async.return_value = mock_task

        # Direkter Aufruf der API-Funktion
        response = await convert_chat_to_document(
            session_id=session_id,
            document_title=None,
            current_user=user,
            db=test_db,
        )

    # --- Assertions ---
    # 1. Celery-Task wurde dispatched
    mock_celery.apply_async.assert_called_once()
    call_kwargs = mock_celery.apply_async.call_args
    args_list = call_kwargs.kwargs.get("args") or call_kwargs.args[0]
    assert str(fake_document.id) in args_list, (
        "Celery-Task sollte mit document_id aufgerufen werden"
    )

    # 2. Document ist QUEUED (nicht mehr PROCESSED) und hat task_id
    test_db.refresh(fake_document)
    assert fake_document.status == DocumentStatus.QUEUED, (
        f"Status sollte QUEUED sein, ist aber {fake_document.status}"
    )
    assert fake_document.task_id == "celery-task-id-abc", (
        "task_id sollte für Celery-Tracking gesetzt sein"
    )

    # 3. API-Response weiterhin korrekt
    assert response.success is True
    assert response.document_id == fake_document.id
    assert "Chat:" in response.document_title
