"""TF-399 Part B — personal (per-user) document-tag assignments.

A ``user``-scope tag is personal vocabulary (``created_by`` the user). Before
TF-399 attaching *any* tag required document ownership and the assignment lived
in the shared ``document_tags`` table — so a user could not group a foreign,
institution-visible document with their own tags, and an assignment would have
been visible to everyone.

This module pins the new contract:

* A ``user``-scope tag attaches to **any document the user can see** (incl.
  foreign ``institution``-visible docs) and lands in ``document_personal_tags``.
* ``institution``/``global``-scope tag assignments stay **owner-only** + shared.
* Personal assignments are **isolated** between users.
* The library list filter (``tag_ids``) matches a document via the caller's own
  personal assignments, not another user's.

Endpoints are called directly (same pattern as ``test_document_tags.py``).
"""

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import func

from api.documents import (
    AttachTagsRequest,
    attach_document_tags,
    detach_document_tag,
    get_document,
    list_documents,
)
from models.auth import AuditLog, Institution, User
from models.document import Document, DocumentStatus, DocumentVisibility
from models.tag import DocumentPersonalTag, DocumentTag, Tag


def _shared_tag_audit_rows(db, document_id):
    """``update_document`` audit rows that record a *shared* tag change.

    Returns ``(AuditLog, parsed_additional_data)`` tuples whose
    ``field == "shared_tags"`` — i.e. the rows our owner-only attach/detach
    audit writes. Personal (``user``-scope) assignments never produce one.
    """
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
        if data.get("field") == "shared_tags":
            out.append((r, data))
    return out


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _attach(document_id, tag_ids, user, db):
    return _run(
        attach_document_tags(
            document_id=document_id,
            body=AttachTagsRequest(tag_ids=tag_ids),
            request=None,
            current_user=user,
            db=db,
        )
    )


def _detach(document_id, tag_id, user, db):
    return _run(
        detach_document_tag(
            document_id=document_id,
            tag_id=tag_id,
            request=None,
            current_user=user,
            db=db,
        )
    )


def _get(document_id, user, db):
    return _run(
        get_document(document_id=document_id, request=None, current_user=user, db=db)
    )


def _list(user, db, tag_ids=None):
    return _run(
        list_documents(
            tag_ids=tag_ids,
            request=None,
            current_user=user,
            db=db,
        )
    )


@pytest.fixture
def stage(test_db):
    # IDs are DB-assigned (autoincrement) and email/slug are namespaced: hard-coded
    # IDs collided with another test's committed rows in the full CI suite. We
    # reference everything via the returned objects' ``.id`` after flush/commit.
    inst = Institution(
        name="TF399P Inst",
        slug="tf399p-inst-personal",
        subscription_tier="professional",
        max_users=50,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()

    def _user(email, *, superuser=False):
        return User(
            email=email,
            first_name="U",
            last_name="T",
            password_hash="x",
            institution_id=inst.id,
            status="active",
            is_superuser=superuser,
        )

    owner = _user("tf399p-owner@example.test")
    alice = _user("tf399p-alice@example.test")
    bob = _user("tf399p-bob@example.test")
    root = _user("tf399p-root@example.test", superuser=True)
    test_db.add_all([owner, alice, bob, root])
    test_db.flush()

    # Institution-visible doc owned by `owner` — alice/bob can see but not own it.
    doc = Document(
        filename="shared.pdf",
        original_filename="Shared.pdf",
        file_path="/tmp/shared.pdf",
        file_size=10,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=inst.id,
        user_id=owner.id,
        visibility=DocumentVisibility.INSTITUTION,
    )
    test_db.add(doc)

    # Personal vocab: a user-scope tag per user (created_by-scoped visibility).
    alice_tag = Tag(name="Alice Wichtig", scope="user", created_by=alice.id)
    bob_tag = Tag(name="Bob Egal", scope="user", created_by=bob.id)
    # Shared institution tag.
    inst_tag = Tag(name="Lehrgang A", scope="institution", institution_id=inst.id)
    test_db.add_all([alice_tag, bob_tag, inst_tag])
    test_db.commit()

    return SimpleNamespace(
        owner=owner,
        alice=alice,
        bob=bob,
        root=root,
        doc=doc,
        alice_tag=alice_tag,
        bob_tag=bob_tag,
        inst_tag=inst_tag,
    )


def test_user_scope_tag_attaches_to_foreign_visible_doc(stage, test_db):
    """Alice tags a doc she can see but does not own -> personal assignment."""
    resp = _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)

    # Personal row exists, scoped to Alice.
    rows = (
        test_db.query(DocumentPersonalTag)
        .filter_by(document_id=stage.doc.id, user_id=stage.alice.id)
        .all()
    )
    assert [r.tag_id for r in rows] == [stage.alice_tag.id]

    # No shared row was created.
    assert test_db.query(DocumentTag).filter_by(document_id=stage.doc.id).count() == 0

    # Response shows the tag flagged as personal.
    tag_out = next(t for t in resp.tags if t.id == stage.alice_tag.id)
    assert tag_out.is_personal is True


def test_institution_scope_tag_attach_by_non_owner_is_forbidden(stage, test_db):
    """A non-owner still may not attach a shared institution tag."""
    with pytest.raises(HTTPException) as exc:
        _attach(stage.doc.id, [stage.inst_tag.id], stage.alice, test_db)
    assert exc.value.status_code == 403
    assert test_db.query(DocumentTag).filter_by(document_id=stage.doc.id).count() == 0


def test_owner_can_attach_institution_scope_tag(stage, test_db):
    """Owner keeps the shared-tag path (sanity that the fork didn't break it)."""
    _attach(stage.doc.id, [stage.inst_tag.id], stage.owner, test_db)
    assert (
        test_db.query(DocumentTag)
        .filter_by(document_id=stage.doc.id, tag_id=stage.inst_tag.id)
        .count()
        == 1
    )


def test_personal_assignments_isolated_between_users(stage, test_db):
    """Bob never sees Alice's personal tag on the shared document."""
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)

    alice_view = _get(stage.doc.id, stage.alice, test_db)
    bob_view = _get(stage.doc.id, stage.bob, test_db)

    assert any(t.id == stage.alice_tag.id for t in alice_view.tags)
    assert all(t.id != stage.alice_tag.id for t in bob_view.tags)


def test_detach_personal_tag_removes_only_own_assignment(stage, test_db):
    """Detaching a user-scope tag clears only the caller's personal row."""
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)
    _detach(stage.doc.id, stage.alice_tag.id, stage.alice, test_db)

    assert (
        test_db.query(DocumentPersonalTag)
        .filter_by(document_id=stage.doc.id, user_id=stage.alice.id)
        .count()
        == 0
    )


def test_list_filter_by_personal_tag_scoped_to_caller(stage, test_db):
    """tag_ids filter matches the doc for Alice (who tagged it) but not Bob."""
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)

    alice_list = _list(stage.alice, test_db, tag_ids=[stage.alice_tag.id])
    assert stage.doc.id in {d.id for d in alice_list.documents}

    # Bob has no personal assignment for that tag -> doc not matched for him.
    bob_list = _list(stage.bob, test_db, tag_ids=[stage.alice_tag.id])
    assert stage.doc.id not in {d.id for d in bob_list.documents}


# --- Shared-tag detach permission (symmetric to the attach-deny path) ---------


def test_institution_scope_tag_detach_by_non_owner_is_forbidden(stage, test_db):
    """A non-owner may not detach a shared institution tag, and the link survives.

    Symmetric to ``test_institution_scope_tag_attach_by_non_owner_is_forbidden``:
    the attach side was already covered; this pins the detach side AND asserts
    the shared row is preserved (a regression that 403s *after* deleting, or
    without rollback, would otherwise pass).
    """
    _attach(stage.doc.id, [stage.inst_tag.id], stage.owner, test_db)

    with pytest.raises(HTTPException) as exc:
        _detach(stage.doc.id, stage.inst_tag.id, stage.alice, test_db)
    assert exc.value.status_code == 403

    assert (
        test_db.query(DocumentTag)
        .filter_by(document_id=stage.doc.id, tag_id=stage.inst_tag.id)
        .count()
        == 1
    )


def test_non_owner_detach_of_unknown_tag_id_is_forbidden(stage, test_db):
    """An unknown/deleted tag_id falls through to the owner-only branch.

    A non-owner cannot probe or detach by passing an arbitrary id — they get a
    403, never a silent removal.
    """
    missing_id = (test_db.query(func.max(Tag.id)).scalar() or 0) + 1
    with pytest.raises(HTTPException) as exc:
        _detach(stage.doc.id, missing_id, stage.alice, test_db)
    assert exc.value.status_code == 403


def test_owner_detach_of_unknown_tag_id_is_noop(stage, test_db):
    """An owner detaching a nonexistent tag id is an idempotent 204 no-op."""
    missing_id = (test_db.query(func.max(Tag.id)).scalar() or 0) + 1
    resp = _detach(stage.doc.id, missing_id, stage.owner, test_db)
    assert resp.status_code == 204


# --- Transaction atomicity on a mixed-scope request ---------------------------


def test_mixed_scope_attach_by_non_owner_is_atomic(stage, test_db):
    """A non-owner sending [personal, shared] in one call commits nothing.

    The personal tag is staged first, then the institution tag raises 403
    mid-loop. The endpoint's rollback must drop the already-staged personal row
    — otherwise the personal half of a rejected request would leak.
    """
    with pytest.raises(HTTPException) as exc:
        _attach(
            stage.doc.id,
            [stage.alice_tag.id, stage.inst_tag.id],
            stage.alice,
            test_db,
        )
    assert exc.value.status_code == 403

    assert (
        test_db.query(DocumentPersonalTag)
        .filter_by(document_id=stage.doc.id, user_id=stage.alice.id)
        .count()
        == 0
    )
    assert test_db.query(DocumentTag).filter_by(document_id=stage.doc.id).count() == 0


def test_duplicate_personal_attach_is_idempotent(stage, test_db):
    """Attaching the same personal tag twice yields exactly one row (no PK clash)."""
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)
    assert (
        test_db.query(DocumentPersonalTag)
        .filter_by(
            document_id=stage.doc.id,
            tag_id=stage.alice_tag.id,
            user_id=stage.alice.id,
        )
        .count()
        == 1
    )


def test_detach_isolates_between_users(stage, test_db):
    """Alice detaching her personal tag leaves Bob's personal row untouched.

    Both users personally tag the same document (each with their own user-scope
    tag). A detach that ignored ``user_id`` (deleting by document_id alone) would
    wipe Bob's row too — this pins the per-user scoping the title promises.
    """
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)
    _attach(stage.doc.id, [stage.bob_tag.id], stage.bob, test_db)

    _detach(stage.doc.id, stage.alice_tag.id, stage.alice, test_db)

    assert (
        test_db.query(DocumentPersonalTag)
        .filter_by(document_id=stage.doc.id, user_id=stage.bob.id)
        .count()
        == 1
    )
    assert (
        test_db.query(DocumentPersonalTag)
        .filter_by(document_id=stage.doc.id, user_id=stage.alice.id)
        .count()
        == 0
    )


# --- CASCADE hygiene: deleting the tag or document drops personal rows --------


def test_personal_rows_cascade_on_tag_delete(stage, test_db):
    """Deleting a tag removes its personal assignments (ondelete=CASCADE)."""
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)
    assert (
        test_db.query(DocumentPersonalTag).filter_by(tag_id=stage.alice_tag.id).count()
        == 1
    )

    test_db.delete(test_db.query(Tag).filter_by(id=stage.alice_tag.id).one())
    test_db.flush()

    assert (
        test_db.query(DocumentPersonalTag).filter_by(tag_id=stage.alice_tag.id).count()
        == 0
    )


def test_personal_rows_cascade_on_document_delete(stage, test_db):
    """Deleting a document removes its personal assignments (ondelete=CASCADE)."""
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)
    doc_id = stage.doc.id
    assert test_db.query(DocumentPersonalTag).filter_by(document_id=doc_id).count() == 1

    test_db.delete(test_db.query(Document).filter_by(id=doc_id).one())
    test_db.flush()

    assert test_db.query(DocumentPersonalTag).filter_by(document_id=doc_id).count() == 0


# --- Audit: shared (owner-only) tag changes are recorded, personal ones aren't -


def test_owner_shared_tag_attach_writes_audit_row(stage, test_db):
    """Attaching a shared institution tag writes one ``shared_tags`` audit row."""
    _attach(stage.doc.id, [stage.inst_tag.id], stage.owner, test_db)

    rows = [r for r in _shared_tag_audit_rows(test_db, stage.doc.id)]
    assert len(rows) == 1
    audit, data = rows[0]
    assert audit.user_id == stage.owner.id
    assert data["operation"] == "attach"
    assert data["tag_ids"] == [stage.inst_tag.id]
    assert data["superuser_bypass"] is False


def test_personal_tag_attach_writes_no_audit(stage, test_db):
    """A personal (user-scope) assignment is private -> no audit row."""
    _attach(stage.doc.id, [stage.alice_tag.id], stage.alice, test_db)
    assert _shared_tag_audit_rows(test_db, stage.doc.id) == []


def test_superuser_shared_tag_detach_audits_with_bypass_flag(stage, test_db):
    """A SuperUser detaching a foreign doc's shared tag is audited as a bypass."""
    _attach(stage.doc.id, [stage.inst_tag.id], stage.owner, test_db)

    _detach(stage.doc.id, stage.inst_tag.id, stage.root, test_db)

    detach_rows = [
        (a, d)
        for a, d in _shared_tag_audit_rows(test_db, stage.doc.id)
        if d["operation"] == "detach"
    ]
    assert len(detach_rows) == 1
    audit, data = detach_rows[0]
    assert audit.user_id == stage.root.id
    assert data["superuser_bypass"] is True
    assert data["tag_ids"] == [stage.inst_tag.id]

    # The shared link was actually removed.
    assert (
        test_db.query(DocumentTag)
        .filter_by(document_id=stage.doc.id, tag_id=stage.inst_tag.id)
        .count()
        == 0
    )


# --- TF-397 interaction: prompt-kind tags never enter the document-tag world ---


def test_prompt_kind_user_tag_is_not_attachable(stage, test_db):
    """A user-scope tag with kind='prompt' is invisible to the document picker.

    TF-397 added a ``kind`` dimension. ``visible_tags_for_user`` is restricted to
    ``kind='content'``, so a prompt-classification tag is not attachable to a
    document (personal or shared) — it 404s like any non-visible tag and no
    personal row is written.
    """
    prompt_tag = Tag(
        name="Alice Prompt", scope="user", created_by=stage.alice.id, kind="prompt"
    )
    test_db.add(prompt_tag)
    test_db.commit()

    with pytest.raises(HTTPException) as exc:
        _attach(stage.doc.id, [prompt_tag.id], stage.alice, test_db)
    assert exc.value.status_code == 404

    assert (
        test_db.query(DocumentPersonalTag).filter_by(tag_id=prompt_tag.id).count() == 0
    )
