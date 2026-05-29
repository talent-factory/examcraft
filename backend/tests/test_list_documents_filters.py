"""TF-355: list_documents filters, pagination, sort, stats."""

import asyncio

import pytest
from types import SimpleNamespace

from api.documents import list_documents
from models.auth import Institution, User, UserStatus
from models.document import Document, DocumentStatus, DocumentVisibility
from models.tag import DocumentTag, Tag


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture
def list_data(test_db):
    inst = Institution(
        id=900,
        name="L",
        slug="l-inst",
        subscription_tier="professional",
        max_users=10,
        max_documents=500,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    me = User(
        id=900,
        email="me@l.ch",
        first_name="M",
        last_name="E",
        password_hash="x",
        institution_id=900,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(me)
    test_db.flush()
    for i in range(30):
        test_db.add(
            Document(
                id=9000 + i,
                filename=f"f{i}.pdf",
                original_filename=f"file{i}.pdf",
                file_path=f"/tmp/{i}.pdf",
                file_size=100 + i,
                mime_type="application/pdf",
                status=DocumentStatus.COMPLETED,
                user_id=900,
                institution_id=900,
                visibility=DocumentVisibility.PRIVATE,
            )
        )
    test_db.commit()
    return SimpleNamespace(me=me)


def test_pagination_defaults(list_data, test_db):
    res = _run(list_documents(current_user=list_data.me, db=test_db))
    assert res.total == 30
    assert res.page == 1
    assert res.page_size == 24
    assert res.total_pages == 2
    assert len(res.documents) == 24


def test_pagination_page_2(list_data, test_db):
    res = _run(
        list_documents(page=2, page_size=24, current_user=list_data.me, db=test_db)
    )
    assert res.page == 2
    assert len(res.documents) == 6


def test_page_size_respected(list_data, test_db):
    res = _run(
        list_documents(page=1, page_size=12, current_user=list_data.me, db=test_db)
    )
    assert res.page_size == 12
    assert len(res.documents) == 12
    assert res.total_pages == 3


def test_stats_present_and_visibility_scoped(list_data, test_db):
    res = _run(list_documents(current_user=list_data.me, db=test_db))
    assert res.stats.total == 30
    assert res.stats.processed == 30  # all COMPLETED
    assert res.stats.in_progress == 0
    assert res.stats.with_vectors == 0


def test_search_matches_original_filename(list_data, test_db):
    res = _run(list_documents(q="file7", current_user=list_data.me, db=test_db))
    assert res.total == 1
    assert res.documents[0].original_filename == "file7.pdf"


def test_search_matches_display_name(list_data, test_db):
    doc = test_db.query(Document).filter(Document.id == 9000).first()
    doc.display_name = "Spezielles Mathe-Skript"
    test_db.commit()
    res = _run(list_documents(q="mathe", current_user=list_data.me, db=test_db))
    assert any(d.id == 9000 for d in res.documents)


def test_search_escapes_underscore_wildcard(list_data, test_db):
    # A literal "_" must not behave as the SQL single-char wildcard.
    d = test_db.query(Document).filter(Document.id == 9000).first()
    d.display_name = "Quartal_Q1"
    test_db.commit()
    res = _run(list_documents(q="_", current_user=list_data.me, db=test_db))
    assert {x.id for x in res.documents} == {9000}


def test_search_no_match_returns_empty(list_data, test_db):
    res = _run(list_documents(q="zzz-nichts", current_user=list_data.me, db=test_db))
    assert res.total == 0
    assert res.documents == []
    assert res.stats.total == 30  # stats ignore the search filter


def test_status_group_processing(list_data, test_db):
    # Scope to the fixture user's own docs — other tests may leave committed
    # rows in the shared test DB, so an unscoped "first 5 by id" is unreliable.
    docs = (
        test_db.query(Document)
        .filter(Document.user_id == list_data.me.id)
        .order_by(Document.id)
        .limit(5)
        .all()
    )
    for d in docs[:3]:
        d.status = DocumentStatus.QUEUED
    for d in docs[3:5]:
        d.status = DocumentStatus.PROCESSING
    test_db.commit()
    res = _run(
        list_documents(status=["processing"], current_user=list_data.me, db=test_db)
    )
    assert res.total == 5


def test_status_group_processed_includes_legacy(list_data, test_db):
    d = test_db.query(Document).filter(Document.id == 9000).first()
    d.status = DocumentStatus.PROCESSED  # legacy value
    test_db.commit()
    res = _run(
        list_documents(status=["processed"], current_user=list_data.me, db=test_db)
    )
    assert res.total == 30  # 29 COMPLETED + 1 PROCESSED


def test_invalid_status_group_400(list_data, test_db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _run(list_documents(status=["bogus"], current_user=list_data.me, db=test_db))
    assert exc.value.status_code == 400


def test_mime_family_word(list_data, test_db):
    d = test_db.query(Document).filter(Document.id == 9001).first()
    d.mime_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    test_db.commit()
    res = _run(
        list_documents(mime_family=["word"], current_user=list_data.me, db=test_db)
    )
    assert res.total == 1


def test_mime_family_chat_export(list_data, test_db):
    d = test_db.query(Document).filter(Document.id == 9002).first()
    d.mime_type = "text/plain"
    d.doc_metadata = {"source": "chat_export"}
    test_db.commit()
    res_chat = _run(
        list_documents(mime_family=["chat"], current_user=list_data.me, db=test_db)
    )
    assert {x.id for x in res_chat.documents} == {9002}
    d2 = test_db.query(Document).filter(Document.id == 9003).first()
    d2.mime_type = "text/plain"
    test_db.commit()
    res_text = _run(
        list_documents(mime_family=["text"], current_user=list_data.me, db=test_db)
    )
    assert {x.id for x in res_text.documents} == {9003}


def test_tag_filter_and_semantics(list_data, test_db):
    t1 = Tag(name="T1", scope="user", created_by=900)
    t2 = Tag(name="T2", scope="user", created_by=900)
    test_db.add_all([t1, t2])
    test_db.flush()
    test_db.add_all(
        [
            DocumentTag(document_id=9000, tag_id=t1.id),
            DocumentTag(document_id=9000, tag_id=t2.id),
            DocumentTag(document_id=9001, tag_id=t1.id),
        ]
    )
    test_db.commit()
    res_both = _run(
        list_documents(tag_ids=[t1.id, t2.id], current_user=list_data.me, db=test_db)
    )
    assert {d.id for d in res_both.documents} == {9000}
    res_one = _run(
        list_documents(tag_ids=[t1.id], current_user=list_data.me, db=test_db)
    )
    assert {d.id for d in res_one.documents} == {9000, 9001}


# ---------------------------------------------------------------------------
# Task A: Sort coverage
# ---------------------------------------------------------------------------


def test_sort_size_desc(list_data, test_db):
    res = _run(
        list_documents(
            sort="size_desc", page_size=3, current_user=list_data.me, db=test_db
        )
    )
    sizes = [d.file_size for d in res.documents]
    assert sizes == sorted(sizes, reverse=True)


def test_sort_title_asc_uses_coalesce(list_data, test_db):
    d = test_db.query(Document).filter(Document.id == 9005).first()
    d.display_name = "AAA-first"
    test_db.commit()
    res = _run(
        list_documents(
            sort="title_asc", page_size=1, current_user=list_data.me, db=test_db
        )
    )
    assert res.documents[0].id == 9005


# ---------------------------------------------------------------------------
# Task B: Stats independence + combined filters
# ---------------------------------------------------------------------------


def test_stats_ignore_content_filters_respect_visibility(list_data, test_db):
    res = _run(
        list_documents(
            q="file1", status=["processed"], current_user=list_data.me, db=test_db
        )
    )
    assert res.stats.total == 30
    assert res.stats.processed == 30  # all COMPLETED
    assert res.total <= 30  # documents narrowed by q


def test_combined_filters_paginate(list_data, test_db):
    res = _run(
        list_documents(
            status=["processed"],
            mime_family=["pdf"],
            sort="size_asc",
            page=1,
            page_size=10,
            current_user=list_data.me,
            db=test_db,
        )
    )
    assert res.page_size == 10
    assert len(res.documents) == 10
    assert res.stats.with_vectors == 0


# ---------------------------------------------------------------------------
# B1 regression: NULL-safe text MIME-family filter
# ---------------------------------------------------------------------------


def test_text_mime_filter_with_metadata_no_source_key(list_data, test_db):
    """B1: text/plain doc whose doc_metadata exists but has no 'source' key
    must appear under mime_family=["text"] and must NOT appear under
    mime_family=["chat"]. Before the fix, doc_metadata->>'source' was SQL NULL
    → not_(chat_flag) was NULL → the row was silently dropped from text results.
    """
    d = test_db.query(Document).filter(Document.id == 9010).first()
    d.mime_type = "text/plain"
    d.doc_metadata = {"title": "Lernnotizen"}  # has metadata, but no "source" key
    test_db.commit()

    res_text = _run(
        list_documents(mime_family=["text"], current_user=list_data.me, db=test_db)
    )
    assert 9010 in {x.id for x in res_text.documents}, (
        "text/plain doc with metadata-but-no-source must appear under mime_family=text"
    )

    res_chat = _run(
        list_documents(mime_family=["chat"], current_user=list_data.me, db=test_db)
    )
    assert 9010 not in {x.id for x in res_chat.documents}, (
        "text/plain doc with no source=chat_export must NOT appear under mime_family=chat"
    )


# ---------------------------------------------------------------------------
# B9: pagination edge cases + MIME-OR across families
# ---------------------------------------------------------------------------


def test_page_beyond_total_pages_returns_empty(list_data, test_db):
    """B9: page > total_pages → empty documents list, but total/total_pages are correct."""
    res = _run(
        list_documents(page=99, page_size=24, current_user=list_data.me, db=test_db)
    )
    assert res.documents == []
    assert res.total == 30
    assert res.total_pages == 2  # ceil(30/24)


def test_zero_results_total_pages_is_zero(list_data, test_db):
    """B9: impossible filter → total==0 → total_pages==0."""
    res = _run(
        list_documents(
            q="zzz-absolut-nichts-passt-hier",
            current_user=list_data.me,
            db=test_db,
        )
    )
    assert res.total == 0
    assert res.total_pages == 0
    assert res.documents == []


def test_mime_family_or_pdf_and_word(list_data, test_db):
    """B9: mime_family=["pdf","word"] → OR across families, returns docs of both."""
    # Fixture already has 30 PDFs; change one to Word
    d = test_db.query(Document).filter(Document.id == 9011).first()
    d.mime_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    test_db.commit()

    # page_size=96 to fetch all 30 docs in one page (default 24 may miss doc 9011
    # if it sorts outside the first page due to non-deterministic created_at ordering)
    res = _run(
        list_documents(
            mime_family=["pdf", "word"],
            page_size=96,
            current_user=list_data.me,
            db=test_db,
        )
    )
    mime_types = {doc.mime_type for doc in res.documents}
    assert "application/pdf" in mime_types
    assert (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in mime_types
    )
    assert res.total == 30  # 29 pdf (9011 changed to word) + 1 word = 30 total
