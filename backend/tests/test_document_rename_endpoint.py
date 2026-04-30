"""
Integration-Tests for PATCH /api/v1/documents/{id} (TF-331).

Ruft die Endpoint-Funktion direkt auf — selbe Pattern wie
``test_documents_superuser_access.py``, das die TestClient/Lifespan-
Komplexität vermeidet.

Coverage:
* Happy path: Owner setzt display_name → 200 + persisted
* Idempotenz: zweiter PATCH mit gleichem Wert → bleibt stabil
* Clear-Override: null/empty/whitespace → display_name=None
* Pydantic-Validation: 256 Zeichen → ValidationError
* Pydantic-Validation: Steuerzeichen → ValidationError
* Tenant-Isolation: User aus anderer Institution → 403
* 404 wenn Dokument nicht existiert
"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.documents import DocumentRenameRequest, rename_document
from models.auth import Institution, User, UserStatus
from models.document import Document, DocumentStatus


@pytest.fixture
def stage_data(test_db):
    """Owner + Foreign-User in unterschiedlichen Institutionen + Doc."""
    inst_a = Institution(
        id=300,
        name="Inst A",
        slug="inst-a",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    inst_b = Institution(
        id=301,
        name="Inst B",
        slug="inst-b",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add_all([inst_a, inst_b])
    test_db.flush()

    owner = User(
        id=300,
        email="owner@a.ch",
        first_name="O",
        last_name="W",
        password_hash="x",
        institution_id=300,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    foreign = User(
        id=301,
        email="foreign@b.ch",
        first_name="F",
        last_name="O",
        password_hash="x",
        institution_id=301,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add_all([owner, foreign])
    test_db.flush()

    doc = Document(
        id=600,
        filename="paper.pdf",
        original_filename="Paper-Final.pdf",
        file_path="/tmp/paper.pdf",
        file_size=10,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=300,
        user_id=300,
        doc_metadata={"title": "1"},  # the bug TF-331 surfaces
    )
    test_db.add(doc)
    test_db.commit()
    return SimpleNamespace(owner=owner, foreign=foreign, doc=doc)


def _run(coro):
    """Run an async coroutine synchronously (for endpoint functions)."""
    return asyncio.new_event_loop().run_until_complete(coro)


def _call(payload, *, document_id, current_user, db):
    """Invoke the rename endpoint directly with the given payload."""
    return _run(
        rename_document(
            document_id=document_id,
            payload=payload,
            request=None,
            current_user=current_user,
            db=db,
        )
    )


# ---------------------------------------------------------------------------
# Pydantic-level validation (runs before the handler)
# ---------------------------------------------------------------------------


def test_pydantic_rejects_string_over_255_chars():
    """Pydantic raises before the handler runs."""
    with pytest.raises(ValidationError, match="(?i)255"):
        DocumentRenameRequest(display_name="x" * 256)


def test_pydantic_rejects_control_characters():
    """ASCII control chars must not enter the DB."""
    with pytest.raises(ValidationError, match="(?i)control"):
        DocumentRenameRequest(display_name="hello\x00world")


def test_pydantic_normalises_whitespace_to_none():
    """Whitespace-only is the clear-override signal."""
    assert DocumentRenameRequest(display_name="   ").display_name is None
    assert DocumentRenameRequest(display_name="\t\n").display_name is None
    assert DocumentRenameRequest(display_name="").display_name is None


def test_pydantic_strips_surrounding_whitespace():
    """Trim padding so cosmetic whitespace doesn't pollute storage."""
    assert DocumentRenameRequest(display_name="  My Doc  ").display_name == "My Doc"


# ---------------------------------------------------------------------------
# Handler-level integration (runs against the real DB transaction)
# ---------------------------------------------------------------------------


def test_owner_sets_display_name_returns_200_and_persists(stage_data, test_db):
    """Happy path: rename succeeds, response and DB both updated."""
    s = stage_data
    payload = DocumentRenameRequest(display_name="Pareto-Cheatsheet")
    result = _call(payload, document_id=s.doc.id, current_user=s.owner, db=test_db)

    # Pydantic response
    assert result.display_name == "Pareto-Cheatsheet"
    assert result.title == "Pareto-Cheatsheet"  # resolver still returns override

    # DB verification (refresh to clear identity map cache)
    test_db.refresh(s.doc)
    assert s.doc.display_name == "Pareto-Cheatsheet"


def test_clear_override_via_null_falls_back_to_filename(stage_data, test_db):
    """Setting display_name=null restores the resolver chain."""
    s = stage_data
    s.doc.display_name = "Old Name"
    test_db.commit()

    payload = DocumentRenameRequest(display_name=None)
    result = _call(payload, document_id=s.doc.id, current_user=s.owner, db=test_db)

    assert result.display_name is None
    # metadata.title is "1" → blocked → falls back to filename stem
    assert result.title == "Paper-Final"
    test_db.refresh(s.doc)
    assert s.doc.display_name is None


def test_clear_override_via_empty_string_works_too(stage_data, test_db):
    """Empty string normalises to None (Pydantic validator)."""
    s = stage_data
    s.doc.display_name = "Old Name"
    test_db.commit()

    payload = DocumentRenameRequest(display_name="   ")
    result = _call(payload, document_id=s.doc.id, current_user=s.owner, db=test_db)

    assert result.display_name is None


def test_idempotent_rename_keeps_state_stable(stage_data, test_db):
    """Two PATCH calls with the same value end at the same state."""
    s = stage_data
    payload = DocumentRenameRequest(display_name="Stable Name")

    _call(payload, document_id=s.doc.id, current_user=s.owner, db=test_db)
    result = _call(payload, document_id=s.doc.id, current_user=s.owner, db=test_db)

    assert result.display_name == "Stable Name"
    test_db.refresh(s.doc)
    assert s.doc.display_name == "Stable Name"


def test_foreign_institution_user_gets_403(stage_data, test_db):
    """TenantFilter blocks cross-institution rename."""
    s = stage_data
    payload = DocumentRenameRequest(display_name="Hacked")

    with pytest.raises(HTTPException) as exc:
        _call(payload, document_id=s.doc.id, current_user=s.foreign, db=test_db)
    assert exc.value.status_code == 403

    # DB unchanged
    test_db.refresh(s.doc)
    assert s.doc.display_name is None


def test_missing_document_returns_404(stage_data, test_db):
    """Non-existent ID surfaces as a clean 404."""
    s = stage_data
    payload = DocumentRenameRequest(display_name="Anything")

    with pytest.raises(HTTPException) as exc:
        _call(payload, document_id=99999, current_user=s.owner, db=test_db)
    assert exc.value.status_code == 404


def test_response_includes_both_title_and_display_name(stage_data, test_db):
    """API contract: clients get the resolved title AND the raw override."""
    s = stage_data
    payload = DocumentRenameRequest(display_name="Override Name")
    result = _call(payload, document_id=s.doc.id, current_user=s.owner, db=test_db)

    # Both fields are populated — the FE relies on display_name to seed
    # the inline-edit value and on title for the read-only display.
    assert result.display_name == "Override Name"
    assert result.title == "Override Name"
    assert result.original_filename == "Paper-Final.pdf"
