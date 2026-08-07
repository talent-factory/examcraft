"""Integration tests for GET /api/v1/documents/{id}/raw.

Calls the endpoint function directly (sister convention to
``test_document_rename_endpoint.py``) to avoid TestClient / lifespan setup.
"""

import asyncio
import os
import tempfile
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

from api.documents import download_document, get_document_raw
from models.auth import Institution, User, UserStatus
from models.document import Document, DocumentStatus


def _run(coro):
    """Run a coroutine to completion in a one-shot event loop.

    Using ``asyncio.run`` rather than a manual ``new_event_loop`` ensures the
    loop and its file descriptors are closed afterwards, preventing the
    "There is no current event loop" warnings on Python 3.13+.
    """
    return asyncio.run(coro)


def _call_raw(*, document_id, current_user, db):
    return _run(
        get_document_raw(
            document_id=document_id,
            request=None,
            current_user=current_user,
            db=db,
        )
    )


def _call_download(*, document_id, current_user, db):
    return _run(
        download_document(
            document_id=document_id,
            request=None,
            current_user=current_user,
            db=db,
        )
    )


@pytest.fixture
def stage_data(test_db):
    """Owner + Foreign-User in unterschiedlichen Institutionen + zwei Docs."""
    inst_a = Institution(
        id=400,
        name="Inst A",
        slug="inst-a-raw",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    inst_b = Institution(
        id=401,
        name="Inst B",
        slug="inst-b-raw",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add_all([inst_a, inst_b])
    test_db.flush()

    owner = User(
        id=400,
        email="owner@a-raw.ch",
        first_name="O",
        last_name="W",
        password_hash="x",
        institution_id=400,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    foreign = User(
        id=401,
        email="foreign@b-raw.ch",
        first_name="F",
        last_name="O",
        password_hash="x",
        institution_id=401,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add_all([owner, foreign])
    test_db.flush()

    # Lokale Datei für PDF-Test anlegen
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode="wb")
    tmp.write(b"%PDF-1.4 minimal")
    tmp.close()

    pdf_doc = Document(
        id=700,
        filename="paper.pdf",
        original_filename="Paper Final.pdf",
        file_path=tmp.name,
        file_size=os.path.getsize(tmp.name),
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=400,
        user_id=400,
        doc_metadata={"title": "Paper"},
    )

    chat_doc = Document(
        id=701,
        filename="chat.md",
        original_filename="Chat-Export.md",
        file_path="virtual://chat/701",
        file_size=42,
        mime_type="text/markdown",
        status=DocumentStatus.PROCESSED,
        institution_id=400,
        user_id=400,
        doc_metadata={
            "source": "chat_export",
            "full_content": "# Frage\n\nWas ist 1+1?\n\n## Antwort\n\n2",
        },
    )

    chat_empty_doc = Document(
        id=702,
        filename="chat-empty.md",
        original_filename="Empty.md",
        file_path="virtual://chat/702",
        file_size=0,
        mime_type="text/markdown",
        status=DocumentStatus.PROCESSED,
        institution_id=400,
        user_id=400,
        doc_metadata={"source": "chat_export"},  # full_content fehlt
    )

    s3_doc = Document(
        id=704,
        filename="s3-paper.pdf",
        original_filename="S3 Paper.pdf",
        # uploads/-Prefix triggert den S3-Pfad in _build_document_file_response
        file_path="uploads/inst-400/s3-paper.pdf",
        file_size=128,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=400,
        user_id=400,
    )

    missing_doc = Document(
        id=703,
        filename="ghost.pdf",
        original_filename="Ghost.pdf",
        file_path="/tmp/this-path-does-not-exist-tf332.pdf",
        file_size=10,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=400,
        user_id=400,
    )

    test_db.add_all([pdf_doc, chat_doc, chat_empty_doc, s3_doc, missing_doc])
    test_db.commit()

    yield SimpleNamespace(
        owner=owner,
        foreign=foreign,
        pdf=pdf_doc,
        chat=chat_doc,
        chat_empty=chat_empty_doc,
        s3=s3_doc,
        missing=missing_doc,
        pdf_path=tmp.name,
    )

    # Cleanup
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_raw_chat_export_returns_inline_markdown(stage_data):
    """Chat-Export liefert full_content als Response mit inline-Disposition."""
    response = _call_raw(
        document_id=stage_data.chat.id,
        current_user=stage_data.owner,
        db=_db_from_stage(stage_data),
    )
    assert isinstance(response, Response)
    # text/* responses are sent with charset=utf-8 so non-ASCII chars
    # (umlauts, en-dash, …) decode unambiguously in older clients.
    assert response.media_type == "text/markdown; charset=utf-8"
    body = response.body.decode("utf-8")
    assert "Frage" in body and "Antwort" in body
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("inline;")
    # RFC 6266: ASCII-quoted + filename* with UTF-8 form. urllib.parse.quote
    # leaves alphanumerics and "-_.~" untouched, so the filename round-trips
    # without percent-encoding here.
    assert 'filename="Chat-Export.md"' in disposition
    assert "filename*=UTF-8''Chat-Export.md" in disposition


def test_raw_local_file_returns_inline_fileresponse(stage_data):
    """Lokale PDF-Datei wird als FileResponse mit inline-Disposition geliefert."""
    response = _call_raw(
        document_id=stage_data.pdf.id,
        current_user=stage_data.owner,
        db=_db_from_stage(stage_data),
    )
    assert isinstance(response, FileResponse)
    assert response.media_type == "application/pdf"
    # FastAPI setzt Content-Disposition aus content_disposition_type+filename
    # erst bei Ausgabe, daher prüfen wir das Attribut direkt
    assert response.headers["content-disposition"].startswith("inline;")


class _FakeStorageService:
    """Minimal storage-service double for the S3 branch in
    _build_document_file_response. ``is_configured`` is a class attribute
    (statt Property), damit monkeypatch.setattr nicht am realen Singleton
    hängenbleibt."""

    is_configured = True

    def __init__(self, download_fn):
        self._download_fn = download_fn

    def download_file(self, path):
        return self._download_fn(path)


def test_raw_s3_backed_file_returns_plain_response_inline(stage_data, monkeypatch):
    """TF-596: S3-Pfad muss eine *plain* ``Response`` liefern, nicht mehr
    ``StreamingResponse(io.BytesIO(...))``.

    ``file_data`` liegt an dieser Stelle bereits vollständig im Speicher
    (TF-595 lädt es komplett via run_in_threadpool). ``StreamingResponse``
    mit einem nicht-async Iterable (``io.BytesIO``) fällt in Starlette auf
    ``iterate_in_threadpool`` zurück, das PRO CHUNK einen eigenen
    Thread-Dispatch macht — und Iteration über ``BytesIO`` ist zeilenbasiert
    (bricht bei jedem ``\\n``-Byte), was bei binären PDF-Daten ~1 Chunk pro
    ~240 Bytes ergibt. Für ein 11.86 MB PDF sind das ~49k Chunks/Dispatches.
    ``Response(content=file_data, ...)`` sendet die Bytes als einzelnen
    Body-Write ohne Iteration.
    """
    from api import documents as documents_api
    from fastapi.responses import StreamingResponse

    fake_pdf_bytes = b"%PDF-1.4 fake S3 payload"
    fake = _FakeStorageService(download_fn=lambda path: fake_pdf_bytes)
    monkeypatch.setattr(documents_api, "storage_service", fake)

    response = _call_raw(
        document_id=stage_data.s3.id,
        current_user=stage_data.owner,
        db=_db_from_stage(stage_data),
    )

    assert isinstance(response, Response)
    assert not isinstance(response, StreamingResponse)
    assert response.body == fake_pdf_bytes
    assert response.media_type == "application/pdf"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("inline;")
    # RFC 6266: spaces (and any non-token char) are percent-encoded.
    assert 'filename="S3%20Paper.pdf"' in disposition
    assert "filename*=UTF-8''S3%20Paper.pdf" in disposition


def test_raw_s3_pdf_sets_identity_content_encoding_to_skip_gzip(
    stage_data, monkeypatch
):
    """TF-596: PDF-Bytes sind bereits komprimiert (FlateDecode-Streams) —
    GZipMiddleware (main.py, minimum_size=1000, kein Content-Type-Ausschluss)
    würde sie sonst zusätzlich CPU-teuer und ergebnislos re-komprimieren.
    ``Content-Encoding: identity`` signalisiert Starlettes GZipMiddleware,
    dass die Response bereits "encoded" ist, und sie überspringt die
    Kompression (siehe ``IdentityResponder.content_encoding_set``-Check)."""
    from api import documents as documents_api

    fake_pdf_bytes = b"%PDF-1.4 fake S3 payload"
    fake = _FakeStorageService(download_fn=lambda path: fake_pdf_bytes)
    monkeypatch.setattr(documents_api, "storage_service", fake)

    response = _call_raw(
        document_id=stage_data.s3.id,
        current_user=stage_data.owner,
        db=_db_from_stage(stage_data),
    )

    assert response.headers["content-encoding"] == "identity"


def test_raw_s3_text_document_keeps_gzip_eligible(stage_data, monkeypatch):
    """Gegenprobe: nicht-binäre/komprimierbare Formate (z. B. text/plain)
    dürfen weiterhin von GZipMiddleware komprimiert werden — kein
    Content-Encoding-Header wird gesetzt, damit die Middleware frei
    entscheiden kann."""
    from api import documents as documents_api

    db = _db_from_stage(stage_data)
    s3_text_doc = Document(
        id=705,
        filename="s3-notes.txt",
        original_filename="S3 Notes.txt",
        file_path="uploads/inst-400/s3-notes.txt",
        file_size=64,
        mime_type="text/plain",
        status=DocumentStatus.PROCESSED,
        institution_id=400,
        user_id=400,
    )
    db.add(s3_text_doc)
    db.commit()

    fake = _FakeStorageService(download_fn=lambda path: b"plain text notes")
    monkeypatch.setattr(documents_api, "storage_service", fake)

    response = _call_raw(
        document_id=705,
        current_user=stage_data.owner,
        db=db,
    )

    assert "content-encoding" not in response.headers


def test_raw_s3_download_does_not_block_event_loop(stage_data, monkeypatch):
    """TF-595: prod runs a single uvicorn worker (--workers 1, Dockerfile.fly),
    so a blocking storage_service.download_file() call inside the async route
    freezes the *entire* backend for every user, not just this request — the
    bigger the document, the longer the freeze.

    Regression guard: run a concurrent "ticker" task alongside the S3-backed
    /raw call while download_file is artificially slow. If download_file runs
    directly on the event loop, the ticker never gets scheduled during the
    sleep and barely increments. If it's offloaded to a thread (the fix),
    the ticker keeps ticking while the download is in flight.
    """
    import time

    from api import documents as documents_api

    def _slow_download(_path):
        time.sleep(0.25)
        return b"%PDF-1.4 slow S3 payload"

    fake = _FakeStorageService(download_fn=_slow_download)
    monkeypatch.setattr(documents_api, "storage_service", fake)

    async def scenario():
        ticks = 0
        stop = False

        async def ticker():
            nonlocal ticks
            while not stop:
                ticks += 1
                await asyncio.sleep(0.005)

        ticker_task = asyncio.create_task(ticker())
        await get_document_raw(
            document_id=stage_data.s3.id,
            request=None,
            current_user=stage_data.owner,
            db=_db_from_stage(stage_data),
        )
        stop = True
        await ticker_task
        return ticks

    ticks = asyncio.run(scenario())
    # ~0.25s of sleep at a 0.005s tick interval yields ~50 ticks when the
    # event loop stays free. If the download blocks the loop, ticks stays
    # at 0 or 1. 5 is a generous floor well below "unblocked" and well
    # above "blocked", so this isn't flaky under CI scheduling jitter.
    assert ticks > 5, (
        f"only {ticks} ticks during the S3 download — the event loop was "
        "blocked (storage_service.download_file must run in a thread)"
    )


def test_raw_s3_file_not_found_returns_404(stage_data, monkeypatch):
    """S3-Pfad: download_file wirft FileNotFoundError → 404."""
    from api import documents as documents_api

    def _raise_not_found(_):
        raise FileNotFoundError("not in bucket")

    fake = _FakeStorageService(download_fn=_raise_not_found)
    monkeypatch.setattr(documents_api, "storage_service", fake)

    with pytest.raises(HTTPException) as exc:
        _call_raw(
            document_id=stage_data.s3.id,
            current_user=stage_data.owner,
            db=_db_from_stage(stage_data),
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_raw_404_missing_document(stage_data):
    with pytest.raises(HTTPException) as exc:
        _call_raw(
            document_id=99999,
            current_user=stage_data.owner,
            db=_db_from_stage(stage_data),
        )
    assert exc.value.status_code == 404


def test_raw_404_chat_export_without_full_content(stage_data):
    with pytest.raises(HTTPException) as exc:
        _call_raw(
            document_id=stage_data.chat_empty.id,
            current_user=stage_data.owner,
            db=_db_from_stage(stage_data),
        )
    assert exc.value.status_code == 404


def test_raw_404_local_file_missing_on_disk(stage_data):
    with pytest.raises(HTTPException) as exc:
        _call_raw(
            document_id=stage_data.missing.id,
            current_user=stage_data.owner,
            db=_db_from_stage(stage_data),
        )
    assert exc.value.status_code == 404


def test_raw_404_foreign_tenant(stage_data):
    """User aus anderer Institution darf nicht zugreifen (kein Superuser).

    TF-354: Das Dokument ist ``private`` (Default). Der visibility-Gate liefert
    404 statt 403, damit die Existenz des fremden Dokuments nicht leakt.
    """
    with pytest.raises(HTTPException) as exc:
        _call_raw(
            document_id=stage_data.pdf.id,
            current_user=stage_data.foreign,
            db=_db_from_stage(stage_data),
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Regression: /download bleibt nach Refactor weiterhin attachment
# ---------------------------------------------------------------------------


def test_download_still_uses_attachment_disposition(stage_data):
    """Sicherstellen, dass das Refactoring /download nicht versehentlich auf
    inline umgestellt hat (Backwards-Compat-Garantie)."""
    response = _call_download(
        document_id=stage_data.pdf.id,
        current_user=stage_data.owner,
        db=_db_from_stage(stage_data),
    )
    assert response.headers["content-disposition"].startswith("attachment;")


def test_download_chat_export_still_attachment(stage_data):
    response = _call_download(
        document_id=stage_data.chat.id,
        current_user=stage_data.owner,
        db=_db_from_stage(stage_data),
    )
    assert isinstance(response, Response)
    assert response.headers["content-disposition"].startswith("attachment;")


def test_download_s3_path_still_attachment(stage_data, monkeypatch):
    """S3-backed /download keeps attachment-disposition after the refactor."""
    from api import documents as documents_api

    fake_pdf_bytes = b"%PDF-1.4 fake S3 download"
    fake = _FakeStorageService(download_fn=lambda _: fake_pdf_bytes)
    monkeypatch.setattr(documents_api, "storage_service", fake)

    response = _call_download(
        document_id=stage_data.s3.id,
        current_user=stage_data.owner,
        db=_db_from_stage(stage_data),
    )
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert 'filename="S3%20Paper.pdf"' in disposition


# ---------------------------------------------------------------------------
# Additional coverage: error categorisation, MIME breadth, header safety,
# superuser policy
# ---------------------------------------------------------------------------


def test_raw_s3_generic_exception_returns_500(stage_data, monkeypatch):
    """Untyped exception from storage_service → outer 500.

    Locks in the mapping so a future refactor of the try/except cannot
    silently downgrade S3 outages to 200 / empty bodies.
    """
    from api import documents as documents_api

    def _raise_runtime(_):
        raise RuntimeError("connection reset")

    fake = _FakeStorageService(download_fn=_raise_runtime)
    monkeypatch.setattr(documents_api, "storage_service", fake)

    with pytest.raises(HTTPException) as exc:
        _call_raw(
            document_id=stage_data.s3.id,
            current_user=stage_data.owner,
            db=_db_from_stage(stage_data),
        )
    assert exc.value.status_code == 500


def test_raw_superuser_from_other_tenant_can_access(stage_data):
    """TenantFilter.verify_tenant_access bypasses tenant for superusers.

    Pins the policy decision so a future tightening of TenantFilter doesn't
    silently break support tooling. Flip this test if the intent changes.
    """
    superuser = User(
        id=499,
        email="root@b-raw.ch",
        first_name="R",
        last_name="O",
        password_hash="x",
        institution_id=401,  # different institution from the document owner
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db = _db_from_stage(stage_data)
    db.add(superuser)
    db.commit()

    response = _call_raw(
        document_id=stage_data.pdf.id,
        current_user=superuser,
        db=db,
    )
    assert isinstance(response, FileResponse)
    assert response.media_type == "application/pdf"


def test_raw_plaintext_document_returns_inline_text(stage_data):
    """Plain-text local file → media_type=text/plain;charset=utf-8, inline."""
    db = _db_from_stage(stage_data)
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb")
    tmp.write("hallo welt — mit umlaut".encode("utf-8"))
    tmp.close()
    try:
        txt_doc = Document(
            id=720,
            filename="hello.txt",
            original_filename="Hallo Welt.txt",
            file_path=tmp.name,
            file_size=os.path.getsize(tmp.name),
            mime_type="text/plain",
            status=DocumentStatus.PROCESSED,
            institution_id=400,
            user_id=400,
        )
        db.add(txt_doc)
        db.commit()

        response = _call_raw(
            document_id=720,
            current_user=stage_data.owner,
            db=db,
        )
        assert isinstance(response, FileResponse)
        # FastAPI/Starlette adds the charset for text/* automatically when
        # given a media_type that already carries it; we set
        # text/plain;charset=utf-8 in _resolve_media_type.
        assert response.media_type.startswith("text/plain")
        assert "charset=utf-8" in response.media_type
        assert response.headers["content-disposition"].startswith("inline;")
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


def test_raw_docx_local_file_returns_correct_mime(stage_data):
    """DOCX MIME comes back verbatim — frontend dispatch depends on this."""
    db = _db_from_stage(stage_data)
    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False, mode="wb")
    tmp.write(b"PK\x03\x04 fake docx zip header")
    tmp.close()
    try:
        docx_doc = Document(
            id=721,
            filename="report.docx",
            original_filename="Report.docx",
            file_path=tmp.name,
            file_size=os.path.getsize(tmp.name),
            mime_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            status=DocumentStatus.PROCESSED,
            institution_id=400,
            user_id=400,
        )
        db.add(docx_doc)
        db.commit()

        response = _call_raw(
            document_id=721,
            current_user=stage_data.owner,
            db=db,
        )
        assert isinstance(response, FileResponse)
        assert response.media_type == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


def test_resolve_media_type_falls_back_when_mime_is_missing():
    """Helper unit test — corrupt rows with NULL mime_type still get a
    safe media_type so the iframe doesn't break.

    The DB schema has NOT NULL on `mime_type`, so we exercise the helper
    directly with a stand-in object rather than persisting a bad row.
    """
    from api.documents import _resolve_media_type

    # No mime, unknown extension → octet-stream floor.
    obj = SimpleNamespace(id=999, mime_type=None, original_filename="weird.qqq")
    assert _resolve_media_type(obj) == "application/octet-stream"

    # No mime, recognisable extension → mimetypes.guess_type wins.
    obj = SimpleNamespace(id=999, mime_type=None, original_filename="hello.txt")
    assert _resolve_media_type(obj).startswith("text/plain")

    # text/* always gets a charset appended.
    obj = SimpleNamespace(id=999, mime_type="text/markdown", original_filename="x.md")
    assert _resolve_media_type(obj) == "text/markdown; charset=utf-8"

    # PDF passes through verbatim — no charset on binary types.
    obj = SimpleNamespace(
        id=999, mime_type="application/pdf", original_filename="x.pdf"
    )
    assert _resolve_media_type(obj) == "application/pdf"


def test_raw_filename_with_crlf_is_safely_quoted(stage_data):
    """RFC 6266 quoting prevents CRLF injection from a malicious filename."""
    db = _db_from_stage(stage_data)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode="wb")
    tmp.write(b"%PDF-1.4 minimal")
    tmp.close()
    try:
        evil = Document(
            id=723,
            filename="evil.pdf",
            # Embedded CRLF + quote attempts header injection.
            original_filename='evil"\r\nX-Injected: yes.pdf',
            file_path=tmp.name,
            file_size=os.path.getsize(tmp.name),
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSED,
            institution_id=400,
            user_id=400,
        )
        db.add(evil)
        db.commit()

        response = _call_raw(
            document_id=723,
            current_user=stage_data.owner,
            db=db,
        )
        disposition = response.headers["content-disposition"]
        # The injection vector requires *literal* CRLF + a real header line.
        # Percent-encoded forms (\\r → %0D, \\n → %0A, ":" → %3A) are inert
        # — they end up as filename characters, not header separators.
        assert "\r" not in disposition
        assert "\n" not in disposition
        # The exact injected header must not survive in raw form.
        assert "\nX-Injected:" not in disposition
        assert "\r\nX-Injected:" not in disposition
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_from_stage(stage_data):
    """Greife auf die test_db-Session zurück, die das stage_data-Fixture befüllt
    hat. Da die Models bereits committed sind, kann jede Session sie lesen —
    wir nehmen die Session, an die das pdf-Doc gebunden ist."""
    from sqlalchemy.orm import object_session

    return object_session(stage_data.pdf)
