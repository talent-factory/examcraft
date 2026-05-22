"""Tests for the document re-index Celery task (TF-352)."""

from unittest.mock import patch, MagicMock
import pytest

from models.document import Document, DocumentStatus
from tasks.rag_tasks import reindex_document_to_institution


def _make_task_session(test_db):
    """Return a context-manager mock that yields test_db when called.

    The Celery task calls ``db = SessionLocal()`` and then ``db.close()``
    in a finally block.  We want those calls to route to the *same*
    savepoint-isolated session the test is using, so we mock SessionLocal
    to return test_db and swallow the close() so the outer transaction
    remains open for the post-call assertions.
    """
    mock_session = MagicMock(wraps=test_db)
    # Don't actually close the session; we need it alive after the task returns.
    mock_session.close = MagicMock()
    mock_session_local = MagicMock(return_value=mock_session)
    return mock_session_local


def test_reindex_task_clears_pending_flag_on_success(test_db, test_institution):
    doc = Document(
        original_filename="r.pdf",
        filename="r.pdf",
        file_path="/tmp/r.pdf",
        file_size=100,
        mime_type="application/pdf",
        institution_id=test_institution.id,
        status=DocumentStatus.PROCESSED,
        pending_reindex=True,
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    mock_session_local = _make_task_session(test_db)

    with patch("tasks.rag_tasks.SessionLocal", mock_session_local):
        with patch("tasks.rag_tasks._reindex_document_payload") as mock_reindex:
            mock_reindex.return_value = True
            reindex_document_to_institution(doc.id)

    # Refresh from DB; the Celery task used test_db so changes are visible
    test_db.expire_all()
    test_db.refresh(doc)
    assert doc.pending_reindex is False


def test_reindex_task_leaves_flag_on_failure(test_db, test_institution):
    doc = Document(
        original_filename="rf.pdf",
        filename="rf.pdf",
        file_path="/tmp/rf.pdf",
        file_size=100,
        mime_type="application/pdf",
        institution_id=test_institution.id,
        status=DocumentStatus.PROCESSED,
        pending_reindex=True,
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    mock_session_local = _make_task_session(test_db)

    with patch("tasks.rag_tasks.SessionLocal", mock_session_local):
        with patch("tasks.rag_tasks._reindex_document_payload") as mock_reindex:
            mock_reindex.side_effect = RuntimeError("Qdrant unreachable")
            with pytest.raises(RuntimeError):
                reindex_document_to_institution(doc.id)

    test_db.expire_all()
    test_db.refresh(doc)
    assert doc.pending_reindex is True


def test_reindex_task_skips_unknown_document(test_db):
    """Document missing means transfer was rolled back — task must not raise."""
    mock_session_local = _make_task_session(test_db)

    with patch("tasks.rag_tasks.SessionLocal", mock_session_local):
        result = reindex_document_to_institution(999_999)

    assert result is None or result is False


def test_reindex_task_handles_stub_not_implemented_error(test_db, test_institution):
    """With the real (unpatched) helper, NotImplementedError must not propagate.
    The task must return None and leave pending_reindex=True."""
    doc = Document(
        original_filename="stub.pdf",
        filename="stub.pdf",
        file_path="/tmp/stub.pdf",
        file_size=100,
        mime_type="application/pdf",
        institution_id=test_institution.id,
        status=DocumentStatus.PROCESSED,
        pending_reindex=True,
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    mock_session_local = _make_task_session(test_db)

    # Call with the REAL _reindex_document_payload (not patched)
    with patch("tasks.rag_tasks.SessionLocal", mock_session_local):
        result = reindex_document_to_institution(doc.id)

    assert result is None, "Stub path must return None"

    # pending_reindex must still be True — stub did not clear it
    test_db.expire_all()
    test_db.refresh(doc)
    assert doc.pending_reindex is True, (
        "pending_reindex must stay True when stub is active"
    )
