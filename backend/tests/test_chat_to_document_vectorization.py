"""
Tests for chat-to-document vectorization.

Previous behavior: convert-chat-to-document created a DBDocument with a
virtual file_path (/tmp/chat_exports/...) and status=PROCESSED, has_vectors=False.
The chat export therefore did NOT end up in the vector index — a re-upload
workaround was needed.

New behavior: convert-chat-to-document should write a real file and dispatch
the Celery vectorization task, like a normal document upload.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
from datetime import datetime

# Test suite is skipped when the Premium package is not installed
# (e.g. in the Core-only CI job). Pattern mirrors test_question_generation_progress_callback.
pytest.importorskip("premium.api.v1.chat")
pytest.importorskip("premium.models.chat_db")


@pytest.fixture(scope="module")
def _ensure_chat_tables(test_engine):
    """
    Ensures Premium chat tables exist in the test DB.

    conftest.py only imports Core models — premium.models.chat_db therefore
    isn't automatically registered in Base.metadata. This fixture imports the
    Premium models and creates any missing tables.
    """
    import premium.models.chat_db  # noqa: F401  # registers tables
    from database import Base

    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.mark.asyncio
async def test_convert_chat_to_document_dispatches_celery_vectorization(
    test_db, _ensure_chat_tables
):
    """
    Convert-chat-to-document should dispatch a Celery task and set status
    QUEUED, so the chat export is subsequently vectorized (like an upload).
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

    # --- Mocks: document_service.upload_document and Celery ---
    # upload_document() would otherwise write a real file to storage/uploads — mock it.
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

        # Direct call to the API function
        response = await convert_chat_to_document(
            session_id=session_id,
            document_title=None,
            current_user=user,
            db=test_db,
        )

    # --- Assertions ---
    # 1. Celery task was dispatched
    mock_celery.apply_async.assert_called_once()
    call_kwargs = mock_celery.apply_async.call_args
    args_list = call_kwargs.kwargs.get("args") or call_kwargs.args[0]
    assert str(fake_document.id) in args_list, (
        "Celery-Task sollte mit document_id aufgerufen werden"
    )

    # 2. Document is QUEUED (no longer PROCESSED) and has a task_id
    test_db.refresh(fake_document)
    assert fake_document.status == DocumentStatus.QUEUED, (
        f"Status sollte QUEUED sein, ist aber {fake_document.status}"
    )
    assert fake_document.task_id == "celery-task-id-abc", (
        "task_id sollte für Celery-Tracking gesetzt sein"
    )

    # 3. API response still correct
    assert response.success is True
    assert response.document_id == fake_document.id
    assert "Chat:" in response.document_title
