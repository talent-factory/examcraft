"""TF-355: document-tag link table + tag endpoints."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from api.documents import (
    AttachTagsRequest,
    DocumentResponse as _DR,
    DocumentTagCreate,
    attach_document_tags,
    create_document_tag,
    detach_document_tag,
    get_document,
    list_document_tags,
)
from models.auth import Institution, User, UserStatus
from models.document import Document, DocumentStatus, DocumentVisibility
from models.tag import DocumentTag, Tag
from utils.document_tags import (
    attach_tags_to_document,
    detach_tag_from_document,
    visible_tags_for_user,
)


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def _seed_users(test_db):
    """Seed minimal Institution + Users required by FK constraints in this module."""
    inst = Institution(
        id=9001,
        name="TF-355 Test Institution",
        slug="tf355-test-institution",
        subscription_tier="free",
        max_users=100,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.merge(inst)
    test_db.flush()
    for uid in (1, 42, 43):
        user = User(
            id=uid,
            email=f"tf355-user{uid}@test.example",
            first_name="Test",
            last_name=f"User{uid}",
            institution_id=9001,
            status="active",
        )
        test_db.merge(user)
    test_db.flush()


def test_document_tag_model_links_doc_and_tag(test_db):
    tag = Tag(name="Mathe", scope="user", created_by=1)
    test_db.add(tag)
    test_db.flush()
    doc = Document(
        id=9100,
        filename="d.pdf",
        original_filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=1,
        mime_type="application/pdf",
        status=DocumentStatus.COMPLETED,
        user_id=1,
        visibility=DocumentVisibility.PRIVATE,
    )
    test_db.add(doc)
    test_db.flush()

    link = DocumentTag(document_id=doc.id, tag_id=tag.id)
    test_db.add(link)
    test_db.commit()

    rows = test_db.query(DocumentTag).filter_by(document_id=doc.id).all()
    assert len(rows) == 1
    assert rows[0].tag_id == tag.id


def test_ux_tags_user_name_index_present_in_schema(test_db):
    row = test_db.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ux_tags_user_name'")
    ).first()
    assert row is not None, "ux_tags_user_name index missing from schema"
    assert "scope" in row[0].lower()


def test_ux_tags_user_name_enforces_uniqueness_per_owner(test_db):
    from sqlalchemy.exc import IntegrityError

    test_db.add(Tag(name="Dup", scope="user", created_by=42))
    test_db.commit()
    test_db.add(
        Tag(name="dup", scope="user", created_by=42)
    )  # same owner, case-insensitive
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()
    test_db.add(Tag(name="Dup", scope="user", created_by=43))  # different owner is fine
    test_db.commit()


@pytest.fixture
def tag_scope_data(test_db):
    inst = Institution(
        id=800,
        name="T",
        slug="t-inst",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    me = User(
        id=800,
        email="me@t.ch",
        first_name="M",
        last_name="E",
        password_hash="x",
        institution_id=800,
        status=UserStatus.ACTIVE.value,
    )
    other = User(
        id=801,
        email="o@t.ch",
        first_name="O",
        last_name="T",
        password_hash="x",
        institution_id=800,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add_all([me, other])
    test_db.flush()
    my_user_tag = Tag(name="Privat-A", scope="user", created_by=800)
    other_user_tag = Tag(name="Privat-B", scope="user", created_by=801)
    inst_tag = Tag(name="Inst-Tag", scope="institution", institution_id=800)
    global_tag = Tag(name="Global", scope="global", institution_id=None)
    test_db.add_all([my_user_tag, other_user_tag, inst_tag, global_tag])
    test_db.commit()
    return SimpleNamespace(
        me=me,
        other=other,
        my_user_tag=my_user_tag,
        other_user_tag=other_user_tag,
        inst_tag=inst_tag,
        global_tag=global_tag,
    )


def test_visible_tags_include_own_user_inst_global_not_foreign_user(
    tag_scope_data, test_db
):
    d = tag_scope_data
    names = {t.name for t in visible_tags_for_user(test_db, d.me).all()}
    assert {"Privat-A", "Inst-Tag", "Global"} <= names
    assert "Privat-B" not in names  # another user's user-scope tag is hidden


def _doc(test_db, did, owner_id, visibility):
    doc = Document(
        id=did,
        filename=f"{did}.pdf",
        original_filename=f"{did}.pdf",
        file_path=f"/tmp/{did}.pdf",
        file_size=1,
        mime_type="application/pdf",
        status=DocumentStatus.COMPLETED,
        user_id=owner_id,
        institution_id=800,
        visibility=visibility,
    )
    test_db.add(doc)
    test_db.commit()
    return doc


def test_attach_user_tag_to_private_doc_ok(tag_scope_data, test_db):
    d = tag_scope_data
    doc = _doc(test_db, 9200, d.me.id, DocumentVisibility.PRIVATE)
    attach_tags_to_document(test_db, doc, [d.my_user_tag.id], d.me)
    test_db.commit()
    rows = test_db.query(DocumentTag).filter_by(document_id=doc.id).all()
    assert {r.tag_id for r in rows} == {d.my_user_tag.id}


def test_attach_institution_tag_to_private_doc_blocked(tag_scope_data, test_db):
    d = tag_scope_data
    doc = _doc(test_db, 9201, d.me.id, DocumentVisibility.PRIVATE)
    with pytest.raises(HTTPException) as exc:
        attach_tags_to_document(test_db, doc, [d.inst_tag.id], d.me)
    assert exc.value.status_code == 400


def test_attach_institution_tag_to_shared_doc_ok(tag_scope_data, test_db):
    d = tag_scope_data
    doc = _doc(test_db, 9202, d.me.id, DocumentVisibility.INSTITUTION)
    attach_tags_to_document(test_db, doc, [d.inst_tag.id], d.me)
    test_db.commit()
    assert test_db.query(DocumentTag).filter_by(document_id=doc.id).count() == 1


def test_attach_foreign_user_tag_rejected(tag_scope_data, test_db):
    d = tag_scope_data
    doc = _doc(test_db, 9203, d.me.id, DocumentVisibility.PRIVATE)
    with pytest.raises(HTTPException) as exc:
        attach_tags_to_document(test_db, doc, [d.other_user_tag.id], d.me)
    assert exc.value.status_code == 404


def test_attach_is_idempotent(tag_scope_data, test_db):
    d = tag_scope_data
    doc = _doc(test_db, 9204, d.me.id, DocumentVisibility.PRIVATE)
    attach_tags_to_document(test_db, doc, [d.my_user_tag.id], d.me)
    test_db.commit()
    attach_tags_to_document(test_db, doc, [d.my_user_tag.id], d.me)
    test_db.commit()
    assert test_db.query(DocumentTag).filter_by(document_id=doc.id).count() == 1


def test_detach_removes_link(tag_scope_data, test_db):
    d = tag_scope_data
    doc = _doc(test_db, 9205, d.me.id, DocumentVisibility.PRIVATE)
    attach_tags_to_document(test_db, doc, [d.my_user_tag.id], d.me)
    test_db.commit()
    detach_tag_from_document(test_db, doc, d.my_user_tag.id)
    test_db.commit()
    assert test_db.query(DocumentTag).filter_by(document_id=doc.id).count() == 0


def test_list_document_tags_endpoint(tag_scope_data, test_db):
    d = tag_scope_data
    result = _run(list_document_tags(current_user=d.me, db=test_db))
    names = {t.name for t in result}
    assert {"Privat-A", "Inst-Tag", "Global"} <= names
    assert "Privat-B" not in names
    own = {t.name: t.is_own for t in result}
    assert own["Privat-A"] is True
    assert own["Global"] is False


def test_create_user_tag(tag_scope_data, test_db):
    d = tag_scope_data
    body = DocumentTagCreate(name="Neu-User", scope="user")
    out = _run(
        create_document_tag(body=body, request=None, current_user=d.me, db=test_db)
    )
    assert out.scope == "user"
    row = test_db.query(Tag).filter(Tag.name == "Neu-User", Tag.scope == "user").first()
    assert row.created_by == d.me.id


def test_create_user_tag_is_idempotent_per_owner(tag_scope_data, test_db):
    d = tag_scope_data
    body = DocumentTagCreate(
        name="Privat-A", scope="user"
    )  # already exists for me (800)
    out = _run(
        create_document_tag(body=body, request=None, current_user=d.me, db=test_db)
    )
    assert out.id == d.my_user_tag.id  # returns existing, no duplicate


def test_create_institution_tag_requires_admin(tag_scope_data, test_db):
    d = tag_scope_data
    body = DocumentTagCreate(name="Neu-Inst", scope="institution")
    with pytest.raises(HTTPException) as exc:
        _run(
            create_document_tag(body=body, request=None, current_user=d.me, db=test_db)
        )
    assert exc.value.status_code == 403


def test_attach_endpoint_owner_only(tag_scope_data, test_db):
    """Owner can attach; non-owner gets an error (private doc → 404 to not leak existence)."""
    d = tag_scope_data
    doc = _doc(test_db, 9300, d.me.id, DocumentVisibility.PRIVATE)
    body = AttachTagsRequest(tag_ids=[d.my_user_tag.id])
    out = _run(
        attach_document_tags(
            document_id=doc.id, body=body, request=None, current_user=d.me, db=test_db
        )
    )
    assert any(t.id == d.my_user_tag.id for t in out.tags)


def test_attach_nonowner_private_doc_raises_404(tag_scope_data, test_db):
    """B10: non-owner + private doc → exactly 404 (existence non-leak via
    assert_document_visible_for — a 403 would confirm the document exists)."""
    d = tag_scope_data
    doc = _doc(test_db, 9310, d.me.id, DocumentVisibility.PRIVATE)
    body = AttachTagsRequest(tag_ids=[d.my_user_tag.id])
    with pytest.raises(HTTPException) as exc:
        _run(
            attach_document_tags(
                document_id=doc.id,
                body=body,
                request=None,
                current_user=d.other,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


def test_attach_nonowner_institution_doc_raises_403(tag_scope_data, test_db):
    """B10: non-owner + institution-visible doc (same institution) → exactly 403
    (doc is visible → assert_document_visible_for passes → ownership check fires)."""
    d = tag_scope_data
    # institution-scope tag on an institution-visible doc is allowed for the owner;
    # use a user-scope tag that other already has visibility into via their own user tag.
    # We attach d.my_user_tag (owned by me=800); other (801) can see the doc but
    # is not the owner → 403 from _load_owned_document.
    doc = _doc(test_db, 9311, d.me.id, DocumentVisibility.INSTITUTION)
    body = AttachTagsRequest(tag_ids=[d.my_user_tag.id])
    with pytest.raises(HTTPException) as exc:
        _run(
            attach_document_tags(
                document_id=doc.id,
                body=body,
                request=None,
                current_user=d.other,
                db=test_db,
            )
        )
    assert exc.value.status_code == 403


def test_detach_nonowner_private_doc_raises_404(tag_scope_data, test_db):
    """B10 (detach): non-owner + private doc → exactly 404."""
    d = tag_scope_data
    doc = _doc(test_db, 9312, d.me.id, DocumentVisibility.PRIVATE)
    with pytest.raises(HTTPException) as exc:
        _run(
            detach_document_tag(
                document_id=doc.id,
                tag_id=d.my_user_tag.id,
                request=None,
                current_user=d.other,
                db=test_db,
            )
        )
    assert exc.value.status_code == 404


def test_detach_nonowner_institution_doc_raises_403(tag_scope_data, test_db):
    """B10 (detach): non-owner + institution-visible doc → exactly 403."""
    d = tag_scope_data
    doc = _doc(test_db, 9313, d.me.id, DocumentVisibility.INSTITUTION)
    with pytest.raises(HTTPException) as exc:
        _run(
            detach_document_tag(
                document_id=doc.id,
                tag_id=d.my_user_tag.id,
                request=None,
                current_user=d.other,
                db=test_db,
            )
        )
    assert exc.value.status_code == 403


def test_get_document_includes_attached_tags(tag_scope_data, test_db):
    d = tag_scope_data
    doc = _doc(test_db, 9400, d.me.id, DocumentVisibility.PRIVATE)
    attach_tags_to_document(test_db, doc, [d.my_user_tag.id], d.me)
    test_db.commit()
    res = _run(
        get_document(document_id=doc.id, request=None, current_user=d.me, db=test_db)
    )
    assert {t.id for t in res.tags} == {d.my_user_tag.id}


def test_detach_endpoint(tag_scope_data, test_db):
    d = tag_scope_data
    doc = _doc(test_db, 9301, d.me.id, DocumentVisibility.PRIVATE)
    _run(
        attach_document_tags(
            document_id=doc.id,
            body=AttachTagsRequest(tag_ids=[d.my_user_tag.id]),
            request=None,
            current_user=d.me,
            db=test_db,
        )
    )
    _run(
        detach_document_tag(
            document_id=doc.id,
            tag_id=d.my_user_tag.id,
            request=None,
            current_user=d.me,
            db=test_db,
        )
    )
    assert test_db.query(DocumentTag).filter_by(document_id=doc.id).count() == 0


def test_document_response_has_tags_field_default_empty():
    dr = _DR(
        id=1,
        filename="a",
        original_filename="a",
        title="a",
        file_size=1,
        mime_type="application/pdf",
        status="completed",
        user_id=1,
        metadata=None,
        content_preview=None,
        vector_collection=None,
        has_vectors=False,
        created_at=None,
        updated_at=None,
        processed_at=None,
    )
    assert dr.tags == []


# ---------------------------------------------------------------------------
# TF-372: scope CHECK constraint + institution/global name uniqueness
# ---------------------------------------------------------------------------


def test_tags_scope_check_constraint_rejects_invalid_scope(test_db):
    """The DB CHECK ``ck_tags_scope_valid`` makes an illegal scope value
    unrepresentable — not merely discouraged by convention at the write sites."""
    from sqlalchemy.exc import IntegrityError

    test_db.add(Tag(name="Bad", scope="bogus", created_by=1))
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_ux_tags_institution_name_enforces_uniqueness_per_institution(test_db):
    """Institution tag names are case-insensitively unique per institution, but
    the same name in a *different* institution is fine."""
    from sqlalchemy.exc import IntegrityError

    # Second institution for the cross-institution assertion (FK target).
    test_db.merge(
        Institution(
            id=9002,
            name="TF-372 Second Institution",
            slug="tf372-second-institution",
            subscription_tier="free",
            max_users=100,
            max_documents=100,
            max_questions_per_month=1000,
        )
    )
    test_db.commit()

    test_db.add(Tag(name="Fach", scope="institution", institution_id=9001))
    test_db.commit()
    test_db.add(Tag(name="fach", scope="institution", institution_id=9001))  # dup
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()
    # Different institution → allowed.
    test_db.add(Tag(name="Fach", scope="institution", institution_id=9002))
    test_db.commit()


def test_ux_tags_global_name_enforces_uniqueness(test_db):
    """Global tag names are case-insensitively unique."""
    from sqlalchemy.exc import IntegrityError

    test_db.add(Tag(name="Welt", scope="global", institution_id=None))
    test_db.commit()
    test_db.add(Tag(name="welt", scope="global", institution_id=None))  # dup
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_detach_institution_tags_removes_only_institution_scope(
    tag_scope_data, test_db
):
    """detach_institution_tags drops institution-scope links but keeps user/global
    ones — the helper used when a doc leaves institution visibility (TF-369)."""
    from utils.document_tags import detach_institution_tags

    d = tag_scope_data
    doc = _doc(test_db, 9300, d.me.id, DocumentVisibility.INSTITUTION)
    test_db.add_all(
        [
            DocumentTag(document_id=doc.id, tag_id=d.inst_tag.id),
            DocumentTag(document_id=doc.id, tag_id=d.my_user_tag.id),
            DocumentTag(document_id=doc.id, tag_id=d.global_tag.id),
        ]
    )
    test_db.commit()

    removed = detach_institution_tags(test_db, doc)
    test_db.commit()

    assert removed == 1
    remaining = {
        r.tag_id for r in test_db.query(DocumentTag).filter_by(document_id=doc.id).all()
    }
    assert remaining == {d.my_user_tag.id, d.global_tag.id}
