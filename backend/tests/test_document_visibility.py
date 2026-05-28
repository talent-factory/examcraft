"""Integration tests for the document visibility privacy fix (TF-354).

Covers spec section 5.6:
* ``filter_documents_for_user`` permutations {owner, same-inst, foreign,
  superuser} × {private, institution}.
* ``GET /documents/`` list endpoint, same permutation set.
* Single-doc endpoints return 404 (not 403) for a foreign private doc.
* ``PATCH /documents/{id}`` visibility is owner-only and audit-logged.
* Upload persists the chosen visibility; ``institution`` without an
  institution → 400.
* Alembic migration A: new rows default to ``private`` + indexes exist.
* RAG paths (available-documents + generate-exam) respect visibility.

Endpoint functions are called directly (no TestClient/lifespan) — same pattern
as ``test_documents_superuser_access.py``. Calling them directly also bypasses
the ``require_permission`` DI dependency, so each test controls the acting user
explicitly and the in-handler authorization logic is what's under test.
"""

import asyncio
import json
import os
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import text

from api.documents import (
    DocumentPatchRequest,
    download_document,
    get_document,
    get_document_chunks,
    get_document_content,
    get_document_raw,
    get_document_status,
    update_document,
    upload_document,
)
from api.exams import list_documents_with_questions
from api.rag_exams import (
    ContextRetrievalRequest,
    RAGExamRequestModel,
    generate_rag_exam,
    get_available_documents,
    retrieve_context,
)
from models.auth import AuditLog, Institution, User, UserStatus
from models.document import Document, DocumentStatus, DocumentVisibility
from utils.document_visibility import (
    filter_documents_for_user,
    is_document_visible_for,
)


def _run(coro):
    """Run an async coroutine synchronously (for endpoint functions)."""
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture
def vis_data(test_db):
    """Two institutions, four users, one private + one institution doc.

    - ``owner`` (inst A) owns both documents.
    - ``colleague`` (inst A) — same institution, not the owner.
    - ``foreigner`` (inst B) — different institution.
    - ``superuser`` (inst A, is_superuser) — bypasses the filter.
    """
    inst_a = Institution(
        id=700,
        name="Vis A",
        slug="vis-a",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    inst_b = Institution(
        id=701,
        name="Vis B",
        slug="vis-b",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add_all([inst_a, inst_b])
    test_db.flush()

    def _user(uid, email, inst, superuser=False):
        return User(
            id=uid,
            email=email,
            first_name="F",
            last_name="L",
            password_hash="x",
            institution_id=inst,
            status=UserStatus.ACTIVE.value,
            is_superuser=superuser,
        )

    owner = _user(700, "owner@vis.ch", 700)
    colleague = _user(701, "colleague@vis.ch", 700)
    foreigner = _user(702, "foreigner@vis.ch", 701)
    superuser = _user(703, "super@vis.ch", 700, superuser=True)
    test_db.add_all([owner, colleague, foreigner, superuser])
    test_db.flush()

    def _doc(did, visibility):
        return Document(
            id=did,
            filename=f"{did}.pdf",
            original_filename=f"{did}.pdf",
            file_path=f"/tmp/{did}.pdf",
            file_size=10,
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            institution_id=700,
            user_id=700,
            visibility=visibility,
            vector_collection=f"doc_{did}",
        )

    doc_private = _doc(700, DocumentVisibility.PRIVATE)
    doc_institution = _doc(701, DocumentVisibility.INSTITUTION)
    test_db.add_all([doc_private, doc_institution])
    test_db.commit()

    return SimpleNamespace(
        owner=owner,
        colleague=colleague,
        foreigner=foreigner,
        superuser=superuser,
        doc_private=doc_private,
        doc_institution=doc_institution,
    )


# ---------------------------------------------------------------------------
# filter_documents_for_user / is_document_visible_for  (query-level predicate)
# ---------------------------------------------------------------------------


def _visible_ids(user, db):
    q = filter_documents_for_user(db.query(Document), user)
    return {d.id for d in q.all()}


def test_owner_sees_both_documents(vis_data, test_db):
    ids = _visible_ids(vis_data.owner, test_db)
    assert {700, 701} <= ids


def test_same_institution_user_sees_only_shared(vis_data, test_db):
    ids = _visible_ids(vis_data.colleague, test_db)
    assert 701 in ids  # institution-shared
    assert 700 not in ids  # owner's private doc is hidden


def test_foreign_institution_user_sees_neither(vis_data, test_db):
    ids = _visible_ids(vis_data.foreigner, test_db)
    assert 700 not in ids
    assert 701 not in ids


def test_superuser_bypasses_filter(vis_data, test_db):
    ids = _visible_ids(vis_data.superuser, test_db)
    assert {700, 701} <= ids


@pytest.mark.parametrize(
    "user_attr,doc_attr,expected",
    [
        ("owner", "doc_private", True),
        ("owner", "doc_institution", True),
        ("colleague", "doc_private", False),
        ("colleague", "doc_institution", True),
        ("foreigner", "doc_private", False),
        ("foreigner", "doc_institution", False),
        ("superuser", "doc_private", True),
        ("superuser", "doc_institution", True),
    ],
)
def test_is_document_visible_for_permutations(vis_data, user_attr, doc_attr, expected):
    user = getattr(vis_data, user_attr)
    doc = getattr(vis_data, doc_attr)
    assert is_document_visible_for(user, doc) is expected


# ---------------------------------------------------------------------------
# GET /documents/  (list endpoint)
# ---------------------------------------------------------------------------


def _list_ids(user, db):
    resp = _run(get_document_list(user, db))
    return {d.id for d in resp.documents}


def get_document_list(user, db):
    # Thin wrapper so the parametrized helper reads cleanly.
    from api.documents import list_documents

    return list_documents(status=None, request=None, current_user=user, db=db)


def test_list_owner_sees_both(vis_data, test_db):
    ids = _list_ids(vis_data.owner, test_db)
    assert {700, 701} <= ids


def test_list_colleague_hides_private(vis_data, test_db):
    ids = _list_ids(vis_data.colleague, test_db)
    assert 701 in ids
    assert 700 not in ids


def test_list_foreigner_sees_neither(vis_data, test_db):
    ids = _list_ids(vis_data.foreigner, test_db)
    assert 700 not in ids
    assert 701 not in ids


# ---------------------------------------------------------------------------
# Single-doc endpoints — 404 (not 403) for a hidden document
# ---------------------------------------------------------------------------


def test_get_document_owner_ok(vis_data, test_db):
    resp = _run(
        get_document(
            document_id=700, request=None, current_user=vis_data.owner, db=test_db
        )
    )
    assert resp.id == 700
    assert resp.visibility == "private"


def test_get_document_colleague_private_returns_404(vis_data, test_db):
    with pytest.raises(HTTPException) as exc:
        _run(
            get_document(
                document_id=700,
                request=None,
                current_user=vis_data.colleague,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


def test_get_document_colleague_shared_ok(vis_data, test_db):
    resp = _run(
        get_document(
            document_id=701, request=None, current_user=vis_data.colleague, db=test_db
        )
    )
    assert resp.id == 701
    assert resp.visibility == "institution"


def test_get_status_foreigner_private_returns_404(vis_data, test_db):
    with pytest.raises(HTTPException) as exc:
        _run(
            get_document_status(
                document_id=700,
                request=None,
                current_user=vis_data.foreigner,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /documents/{id} — visibility is owner-only + audit-logged
# ---------------------------------------------------------------------------


def test_owner_changes_visibility_and_audit_logged(vis_data, test_db):
    payload = DocumentPatchRequest(visibility=DocumentVisibility.INSTITUTION)
    resp = _run(
        update_document(
            document_id=700,
            payload=payload,
            request=None,
            current_user=vis_data.owner,
            db=test_db,
        )
    )
    assert resp.visibility == "institution"

    test_db.refresh(vis_data.doc_private)
    assert vis_data.doc_private.visibility == DocumentVisibility.INSTITUTION

    logs = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "update_document")
        .filter(AuditLog.resource_id == "700")
        .all()
    )
    assert len(logs) == 1
    extra = json.loads(logs[0].additional_data)
    assert extra["field"] == "visibility"
    assert extra["old_visibility"] == "private"
    assert extra["new_visibility"] == "institution"


def test_non_owner_cannot_change_visibility_of_shared_doc(vis_data, test_db):
    # colleague CAN see the institution-shared doc but is not its owner → 403.
    payload = DocumentPatchRequest(visibility=DocumentVisibility.PRIVATE)
    with pytest.raises(HTTPException) as exc:
        _run(
            update_document(
                document_id=701,
                payload=payload,
                request=None,
                current_user=vis_data.colleague,
                db=test_db,
            )
        )
    assert exc.value.status_code == 403
    test_db.refresh(vis_data.doc_institution)
    assert vis_data.doc_institution.visibility == DocumentVisibility.INSTITUTION


def test_foreigner_cannot_even_see_private_doc_to_patch(vis_data, test_db):
    payload = DocumentPatchRequest(visibility=DocumentVisibility.INSTITUTION)
    with pytest.raises(HTTPException) as exc:
        _run(
            update_document(
                document_id=700,
                payload=payload,
                request=None,
                current_user=vis_data.foreigner,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


def test_no_op_visibility_change_writes_no_audit(vis_data, test_db):
    # Setting the same visibility must not create a spurious audit entry.
    payload = DocumentPatchRequest(visibility=DocumentVisibility.PRIVATE)
    _run(
        update_document(
            document_id=700,
            payload=payload,
            request=None,
            current_user=vis_data.owner,
            db=test_db,
        )
    )
    logs = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "update_document")
        .filter(AuditLog.resource_id == "700")
        .all()
    )
    assert len(logs) == 0


def test_patch_requires_at_least_one_field():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        DocumentPatchRequest()


# ---------------------------------------------------------------------------
# Upload — visibility persistence + institution-without-institution → 400
# ---------------------------------------------------------------------------


def test_upload_institution_without_institution_returns_400(test_db):
    # A user with no institution may not share institution-wide. We call the
    # endpoint directly with a lightweight user — the guard runs before any DB
    # / file access, so no real (NOT NULL institution_id) row is needed.
    no_inst_user = SimpleNamespace(id=999, institution_id=None, is_superuser=False)
    dummy_file = UploadFile(filename="x.pdf", file=BytesIO(b"x"), size=1)

    with pytest.raises(HTTPException) as exc:
        _run(
            upload_document(
                file=dummy_file,
                visibility=DocumentVisibility.INSTITUTION,
                http_request=None,
                current_user=no_inst_user,
                db=test_db,
            )
        )
    assert exc.value.status_code == 400


def test_upload_persists_chosen_visibility(vis_data, test_db, mocker):
    created = {}

    async def fake_upload(file, user_id, db):
        doc = Document(
            filename="up.pdf",
            original_filename="up.pdf",
            file_path="/tmp/up.pdf",
            file_size=5,
            mime_type="application/pdf",
            status=DocumentStatus.UPLOADED,
            user_id=user_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        created["id"] = doc.id
        return doc

    mocker.patch(
        "api.documents.document_service.upload_document", side_effect=fake_upload
    )
    mocker.patch(
        "api.documents.celery_process_document.apply_async",
        return_value=SimpleNamespace(id="task-1"),
    )

    dummy_file = UploadFile(filename="up.pdf", file=BytesIO(b"hello"), size=5)
    _run(
        upload_document(
            file=dummy_file,
            visibility=DocumentVisibility.INSTITUTION,
            http_request=None,
            current_user=vis_data.owner,
            db=test_db,
        )
    )

    doc = test_db.query(Document).filter(Document.id == created["id"]).first()
    assert doc is not None
    assert doc.visibility == DocumentVisibility.INSTITUTION
    assert doc.institution_id == vis_data.owner.institution_id


# ---------------------------------------------------------------------------
# Alembic migration A — default private + indexes
# ---------------------------------------------------------------------------


def test_migration_a_defaults_private_and_creates_indexes(test_db):
    # A row inserted without an explicit visibility must inherit the server
    # default 'private' — the migration's security-first reset.
    test_db.execute(
        text(
            "INSERT INTO documents (filename, original_filename, file_path, "
            "file_size, mime_type) "
            "VALUES ('m.pdf', 'm.pdf', '/tmp/m.pdf', 1, 'application/pdf')"
        )
    )
    value = test_db.execute(
        text("SELECT visibility FROM documents WHERE filename = 'm.pdf'")
    ).scalar()
    assert value == "private"

    # Run the real migration upgrade() against the test connection. It is
    # idempotent over the create_all schema (enum/column guarded), so its net
    # effect here is (re)creating both indexes — which we then assert.
    import importlib.util

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    mig_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "alembic",
        "versions",
        "2026_05_28_tf354_documents_visibility.py",
    )
    spec = importlib.util.spec_from_file_location(
        "tf354_migration_under_test", mig_path
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    ctx = MigrationContext.configure(test_db.connection())
    with Operations.context(ctx):
        migration.upgrade()

    index_names = {
        row[0]
        for row in test_db.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'documents'")
        ).fetchall()
    }
    assert "ix_documents_visibility" in index_names
    assert "ix_documents_inst_vis_created" in index_names


# ---------------------------------------------------------------------------
# RAG paths respect visibility (the section-7 privacy-bypass guards)
# ---------------------------------------------------------------------------


def _available_doc_ids(user, db):
    resp = _run(
        get_available_documents(
            processed_only=True, request=None, current_user=user, db=db
        )
    )
    return {d["id"] for d in resp["documents"]}


def test_rag_available_documents_owner_sees_private(vis_data, test_db):
    ids = _available_doc_ids(vis_data.owner, test_db)
    assert {700, 701} <= ids


def test_rag_available_documents_colleague_hides_private(vis_data, test_db):
    ids = _available_doc_ids(vis_data.colleague, test_db)
    assert 701 in ids
    assert 700 not in ids


def test_rag_generate_rejects_foreign_private_doc(vis_data, test_db):
    # Passing a colleague's private doc id to RAG generation must 404 *before*
    # any Celery dispatch — closing the RAG privacy bypass (spec §7).
    request_model = RAGExamRequestModel(topic="Privacy Test", document_ids=[700])
    with pytest.raises(HTTPException) as exc:
        _run(
            generate_rag_exam(
                request=request_model,
                http_request=None,
                current_user=vis_data.colleague,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


def test_rag_retrieve_context_rejects_foreign_private_doc(vis_data, test_db):
    # retrieve-context returns document *text* — at least as sensitive as
    # generation. A colleague's private doc id must 404 before any vector lookup.
    request_model = ContextRetrievalRequest(query="leak attempt", document_ids=[700])
    with pytest.raises(HTTPException) as exc:
        _run(
            retrieve_context(
                request=request_model,
                http_request=None,
                current_user=vis_data.colleague,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Additional review gaps: content endpoints, 404 indistinguishability,
# SuperUser PATCH, institution-without-institution PATCH, explicit-null PATCH,
# and the exam-composer document list.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "endpoint",
    [download_document, get_document_raw, get_document_content, get_document_chunks],
)
def test_content_endpoints_404_for_foreign_private(vis_data, test_db, endpoint):
    # The file/content/chunk endpoints are the actual exfiltration paths. Each
    # shares assert_document_visible_for, so a foreigner hitting the owner's
    # private doc must 404 *before* any storage / content access.
    with pytest.raises(HTTPException) as exc:
        _run(
            endpoint(
                document_id=700,
                request=None,
                current_user=vis_data.foreigner,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


def test_hidden_doc_404_is_indistinguishable_from_missing(vis_data, test_db):
    # A hidden doc and a truly missing doc must return the SAME 404 detail, so a
    # colleague cannot infer existence from the error body.
    with pytest.raises(HTTPException) as hidden:
        _run(
            get_document(
                document_id=700,
                request=None,
                current_user=vis_data.colleague,
                db=test_db,
            )
        )
    with pytest.raises(HTTPException) as missing:
        _run(
            get_document(
                document_id=999999,
                request=None,
                current_user=vis_data.colleague,
                db=test_db,
            )
        )
    assert hidden.value.status_code == missing.value.status_code == 404
    assert hidden.value.detail == missing.value.detail


def test_superuser_can_change_visibility_of_foreign_doc(vis_data, test_db):
    # SuperUser bypasses the owner-only rule (deliberately preserved).
    payload = DocumentPatchRequest(visibility=DocumentVisibility.INSTITUTION)
    resp = _run(
        update_document(
            document_id=700,
            payload=payload,
            request=None,
            current_user=vis_data.superuser,
            db=test_db,
        )
    )
    assert resp.visibility == "institution"
    test_db.refresh(vis_data.doc_private)
    assert vis_data.doc_private.visibility == DocumentVisibility.INSTITUTION


def test_patch_institution_on_doc_without_institution_returns_400(vis_data, test_db):
    # Sharing a doc that has no institution is rejected at PATCH too (mirrors the
    # upload guard); the document stays private.
    orphan = Document(
        id=720,
        filename="orphan.pdf",
        original_filename="orphan.pdf",
        file_path="/tmp/orphan.pdf",
        file_size=10,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=None,
        user_id=vis_data.owner.id,
        visibility=DocumentVisibility.PRIVATE,
    )
    test_db.add(orphan)
    test_db.commit()

    payload = DocumentPatchRequest(visibility=DocumentVisibility.INSTITUTION)
    with pytest.raises(HTTPException) as exc:
        _run(
            update_document(
                document_id=720,
                payload=payload,
                request=None,
                current_user=vis_data.owner,
                db=test_db,
            )
        )
    assert exc.value.status_code == 400
    test_db.refresh(orphan)
    assert orphan.visibility == DocumentVisibility.PRIVATE


def test_patch_explicit_null_visibility_is_rejected():
    # A body of {"visibility": null} alone is a no-op, not an instruction → 422.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        DocumentPatchRequest(visibility=None)


def test_exam_composer_list_hides_colleague_private_doc(vis_data, test_db):
    # GET /exams/documents-with-questions must not leak a colleague's private
    # doc to other institution members; the institution-shared one stays visible.
    # (The existing exam-API tests run as a SuperUser, so they cannot catch this.)
    result = _run(
        list_documents_with_questions(current_user=vis_data.colleague, db=test_db)
    )
    ids = {entry["id"] for entry in result}
    assert 701 in ids  # institution-shared doc visible
    assert 700 not in ids  # owner's private doc hidden
