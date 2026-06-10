"""TF-399 Part A — rename (display_name) is owner-only and always audited.

Before TF-399 a ``display_name`` rename was allowed for *anyone who could see*
the document (``create_documents`` + visibility gate) and was **never** written
to the audit log. ``display_name`` is shared state on the ``Document`` row, so a
non-owner could silently rename a colleague's institution-shared document.

This module pins the corrected contract:

* Same-institution **non-owner** renaming an institution-visible doc -> 403.
* **Owner** rename still succeeds AND writes one ``update_document`` audit row
  carrying ``field=display_name`` (analogous to the visibility-change audit).
* **SuperUser** may rename a foreign doc, and that change is audited too.

Calls the endpoint function directly (same pattern as
``test_document_rename_endpoint.py``) to avoid TestClient/lifespan overhead.
"""

import asyncio
import json

import pytest
from fastapi import HTTPException

from api.documents import DocumentPatchRequest, update_document
from models.auth import AuditLog, Institution, User, UserStatus
from models.document import Document, DocumentStatus, DocumentVisibility


@pytest.fixture
def stage(test_db):
    """Owner + same-institution colleague + a SuperUser, and one
    institution-visible document owned by the owner.

    IDs are DB-assigned and email/slug namespaced — hard-coded IDs collide with
    other tests' committed rows in the full suite. Reference via ``.id``.
    """
    inst = Institution(
        name="TF399R Inst",
        slug="tf399r-inst-shared",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()

    owner = User(
        email="tf399r-owner@example.test",
        first_name="O",
        last_name="W",
        password_hash="x",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    colleague = User(
        email="tf399r-colleague@example.test",
        first_name="C",
        last_name="O",
        password_hash="x",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    root = User(
        email="tf399r-root@example.test",
        first_name="R",
        last_name="T",
        password_hash="x",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    test_db.add_all([owner, colleague, root])
    test_db.flush()

    doc = Document(
        filename="shared.pdf",
        original_filename="Shared-Final.pdf",
        file_path="/tmp/shared.pdf",
        file_size=10,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=inst.id,
        user_id=owner.id,
        visibility=DocumentVisibility.INSTITUTION,
        doc_metadata={"title": "1"},
    )
    test_db.add(doc)
    test_db.commit()

    from types import SimpleNamespace

    return SimpleNamespace(owner=owner, colleague=colleague, root=root, doc=doc)


def _call(payload, *, document_id, current_user, db):
    return asyncio.new_event_loop().run_until_complete(
        update_document(
            document_id=document_id,
            payload=payload,
            request=None,
            current_user=current_user,
            db=db,
        )
    )


def _rename_audit_rows(db, document_id):
    """Audit rows for this document that record a display_name change."""
    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "update_document",
            AuditLog.resource_id == str(document_id),
        )
        .all()
    )
    out = []
    for r in rows:
        data = json.loads(r.additional_data) if r.additional_data else {}
        if data.get("field") == "display_name":
            out.append((r, data))
    return out


def test_same_institution_non_owner_rename_returns_403(stage, test_db):
    """A colleague who can *see* the institution doc still may not rename it."""
    payload = DocumentPatchRequest(display_name="Renamed by colleague")

    with pytest.raises(HTTPException) as exc:
        _call(
            payload,
            document_id=stage.doc.id,
            current_user=stage.colleague,
            db=test_db,
        )
    assert exc.value.status_code == 403

    # Shared state untouched.
    test_db.refresh(stage.doc)
    assert stage.doc.display_name is None


def test_owner_rename_writes_audit_row(stage, test_db):
    """Owner rename succeeds and leaves exactly one display_name audit row."""
    payload = DocumentPatchRequest(display_name="Owner Title")
    result = _call(
        payload, document_id=stage.doc.id, current_user=stage.owner, db=test_db
    )

    assert result.display_name == "Owner Title"

    rows = _rename_audit_rows(test_db, stage.doc.id)
    assert len(rows) == 1
    audit, data = rows[0]
    assert audit.user_id == stage.owner.id
    assert data["new_display_name"] == "Owner Title"
    assert data["old_display_name"] is None


def test_superuser_can_rename_and_audits(stage, test_db):
    """SuperUser bypasses ownership but the change is still audited."""
    payload = DocumentPatchRequest(display_name="Root Edit")
    result = _call(
        payload, document_id=stage.doc.id, current_user=stage.root, db=test_db
    )

    assert result.display_name == "Root Edit"
    rows = _rename_audit_rows(test_db, stage.doc.id)
    assert len(rows) == 1
    assert rows[0][0].user_id == stage.root.id


def test_no_op_rename_to_same_value_writes_no_audit(stage, test_db):
    """Re-sending the current value is not an effective change -> no audit row."""
    stage.doc.display_name = "Already"
    test_db.commit()

    payload = DocumentPatchRequest(display_name="Already")
    _call(payload, document_id=stage.doc.id, current_user=stage.owner, db=test_db)

    assert _rename_audit_rows(test_db, stage.doc.id) == []
