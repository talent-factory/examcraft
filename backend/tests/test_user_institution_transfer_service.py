"""Unit tests for user_institution_transfer_service."""

from models.document import Document, DocumentStatus


def test_document_model_has_pending_reindex_column(test_db, test_institution):
    """Document.pending_reindex muss existieren und default False sein."""
    doc = Document(
        filename="t.pdf",
        original_filename="t.pdf",
        file_path="/tmp/t.pdf",
        file_size=1,
        mime_type="application/pdf",
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)
    assert doc.pending_reindex is False


def test_translation_keys_for_transfer_errors_exist():
    """Alle 3 neuen Translation-Keys müssen in allen Locales liefern."""
    from services.translation_service import t, SUPPORTED_LOCALES

    keys = [
        "admin_transfer_self_forbidden",
        "admin_transfer_same_institution",
        "admin_transfer_audit_failed",
    ]
    for locale in SUPPORTED_LOCALES:
        for key in keys:
            result = t(key, locale=locale)
            assert result, f"Empty translation for {key} in {locale}"
            # Fallback message must not be returned
            fallback_substrings = {
                "de": "Ein Fehler",
                "en": "An error",
                "fr": "Une erreur",
                "it": "Si è verificato",
            }
            assert fallback_substrings[locale] not in result, (
                f"Got fallback for {key}/{locale}: {result}"
            )


def test_transfer_flags_dataclass_is_frozen():
    """TransferFlags is a frozen dataclass — assignment must raise."""
    from services.user_institution_transfer_service import TransferFlags
    import dataclasses
    import pytest

    flags = TransferFlags(documents=True, exams=False, questions=True, tags=False)
    assert flags.documents is True
    assert flags.exams is False
    with pytest.raises(dataclasses.FrozenInstanceError):
        flags.documents = False  # type: ignore[misc]


def test_transfer_stats_dataclass():
    from services.user_institution_transfer_service import TransferStats

    stats = TransferStats(
        documents=2, exams=1, questions=4, tags=0, document_ids=[1, 2]
    )
    assert stats.documents == 2
    assert stats.document_ids == [1, 2]


def test_preview_counts_and_excluded_counts():
    from services.user_institution_transfer_service import (
        PreviewCounts,
        ExcludedCounts,
        TransferPreview,
    )

    p = PreviewCounts(documents=3, exams=1, questions=2, tags=0)
    e = ExcludedCounts(students=10, classes=2, submissions=50)
    tp = TransferPreview(
        transferable=p,
        excluded=e,
        source_institution_id=1,
        source_institution_name="S",
        target_institution_id=2,
        target_institution_name="T",
    )
    assert tp.transferable.documents == 3
    assert tp.excluded.submissions == 50


def test_transfer_error_carries_code_and_status():
    from services.user_institution_transfer_service import TransferError

    err = TransferError("admin_transfer_self_forbidden", http_status=400)
    assert err.code == "admin_transfer_self_forbidden"
    assert err.http_status == 400
    assert str(err) == "admin_transfer_self_forbidden"


def test_preview_returns_correct_counts(test_db, test_institution):
    """Preview returns exact counts per artifact type."""
    from sqlalchemy import text
    from models.auth import User, Institution
    from models.document import Document, DocumentStatus
    from models.exam import Exam
    from models.question_review import QuestionReview
    from models.tag import Tag
    from services.user_institution_transfer_service import preview_transfer

    # Advance sequence past the explicit id=1 used by test_institution fixture
    test_db.execute(
        text("SELECT setval('institutions_id_seq', (SELECT MAX(id) FROM institutions))")
    )
    test_db.commit()

    target = Institution(
        name="Target",
        slug="target",
        domain="target.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    user = User(
        email="preview-t@example.com",
        first_name="t",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add(user)
    test_db.commit()

    # 3 docs
    for i in range(3):
        test_db.add(
            Document(
                filename=f"d{i}.pdf",
                original_filename=f"d{i}.pdf",
                file_path=f"/tmp/d{i}.pdf",
                file_size=100,
                mime_type="application/pdf",
                user_id=user.id,
                institution_id=test_institution.id,
                status=DocumentStatus.UPLOADED,
            )
        )
    # 1 exam
    test_db.add(
        Exam(
            title="e1",
            created_by=user.id,
            institution_id=test_institution.id,
        )
    )
    # 2 question reviews
    for i in range(2):
        test_db.add(
            QuestionReview(
                question_text=f"q{i}",
                question_type="single_choice",
                difficulty="medium",
                topic=f"topic{i}",
                created_by=user.id,
                institution_id=test_institution.id,
            )
        )
    # 1 scoped tag + 1 global tag (global must be excluded)
    test_db.add(
        Tag(name="scoped", created_by=user.id, institution_id=test_institution.id)
    )
    test_db.add(Tag(name="global", created_by=user.id, institution_id=None))
    test_db.commit()

    preview = preview_transfer(test_db, user.id, target.id)
    assert preview.transferable.documents == 3
    assert preview.transferable.exams == 1
    assert preview.transferable.questions == 2
    assert preview.transferable.tags == 1  # global excluded
    assert preview.source_institution_id == test_institution.id
    assert preview.target_institution_id == target.id
    assert preview.target_institution_name == "Target"


def test_preview_excludes_other_institution_artifacts(test_db, test_institution):
    """Documents in a third institution must not count."""
    from sqlalchemy import text
    from models.auth import User, Institution
    from models.document import Document, DocumentStatus
    from services.user_institution_transfer_service import preview_transfer

    # Advance sequence past the explicit id=1 used by test_institution fixture
    test_db.execute(
        text("SELECT setval('institutions_id_seq', (SELECT MAX(id) FROM institutions))")
    )
    test_db.commit()

    target = Institution(
        name="T2",
        slug="t2",
        domain="t2.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    other = Institution(
        name="O",
        slug="o",
        domain="o.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add_all([target, other])
    test_db.commit()

    user = User(
        email="other@x",
        first_name="u",
        last_name="x",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add(user)
    test_db.commit()

    test_db.add(
        Document(
            filename="src.pdf",
            original_filename="src.pdf",
            file_path="/tmp/src.pdf",
            file_size=100,
            mime_type="application/pdf",
            user_id=user.id,
            institution_id=test_institution.id,
            status=DocumentStatus.UPLOADED,
        )
    )
    test_db.add(
        Document(
            filename="other.pdf",
            original_filename="other.pdf",
            file_path="/tmp/other.pdf",
            file_size=100,
            mime_type="application/pdf",
            user_id=user.id,
            institution_id=other.id,
            status=DocumentStatus.UPLOADED,
        )
    )
    test_db.commit()

    preview = preview_transfer(test_db, user.id, target.id)
    assert preview.transferable.documents == 1


def test_preview_raises_for_same_institution(test_db, test_institution):
    from models.auth import User
    from services.user_institution_transfer_service import (
        preview_transfer,
        TransferError,
    )
    import pytest

    user = User(
        email="same@x",
        first_name="s",
        last_name="x",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add(user)
    test_db.commit()

    with pytest.raises(TransferError) as exc:
        preview_transfer(test_db, user.id, test_institution.id)
    assert exc.value.code == "admin_transfer_same_institution"
    assert exc.value.http_status == 400


def test_preview_raises_for_unknown_user(test_db, test_institution):
    from services.user_institution_transfer_service import (
        preview_transfer,
        TransferError,
    )
    import pytest

    with pytest.raises(TransferError) as exc:
        preview_transfer(test_db, 99999, test_institution.id)
    assert exc.value.code == "admin_user_not_found"
    assert exc.value.http_status == 404


def test_preview_raises_for_unknown_target_institution(test_db, test_institution):
    from models.auth import User
    from services.user_institution_transfer_service import (
        preview_transfer,
        TransferError,
    )
    import pytest

    user = User(
        email="ukt@x",
        first_name="u",
        last_name="k",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add(user)
    test_db.commit()

    with pytest.raises(TransferError) as exc:
        preview_transfer(test_db, user.id, 99999)
    assert exc.value.code == "admin_institution_not_found"
    assert exc.value.http_status == 404


def test_transfer_user_moves_all_artifact_types(test_db, test_institution):
    """All flags True: user + all 4 artifact types moved to target."""
    from models.auth import User, Institution
    from models.document import Document, DocumentStatus
    from models.exam import Exam
    from models.question_review import QuestionReview
    from models.tag import Tag
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )

    # Reset PG sequence if needed (Tasks 5 pattern)
    from sqlalchemy import text

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="TG",
        slug="tg",
        domain="tg.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="admin-t6@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    target_user = User(
        email="user-t6@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, target_user])
    test_db.commit()

    doc = Document(
        filename="d.pdf",
        original_filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=target_user.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    exam = Exam(
        title="e", created_by=target_user.id, institution_id=test_institution.id
    )
    review = QuestionReview(
        question_text="q",
        created_by=target_user.id,
        question_type="single_choice",
        difficulty="easy",
        topic="t",
        institution_id=test_institution.id,
    )
    tag = Tag(name="t", created_by=target_user.id, institution_id=test_institution.id)
    test_db.add_all([doc, exam, review, tag])
    test_db.commit()

    flags = TransferFlags(documents=True, exams=True, questions=True, tags=True)
    stats = transfer_user(test_db, target_user.id, target.id, flags, actor)

    assert stats.documents == 1
    assert stats.exams == 1
    assert stats.questions == 1
    assert stats.tags == 1
    assert doc.id in stats.document_ids

    test_db.refresh(target_user)
    test_db.refresh(doc)
    test_db.refresh(exam)
    test_db.refresh(review)
    test_db.refresh(tag)
    assert target_user.institution_id == target.id
    assert doc.institution_id == target.id
    assert doc.pending_reindex is True
    assert exam.institution_id == target.id
    assert review.institution_id == target.id
    assert tag.institution_id == target.id


def test_transfer_respects_per_type_flags(test_db, test_institution):
    """Only documents=True moves documents; exams/questions/tags stay."""
    from models.auth import User, Institution
    from models.document import Document, DocumentStatus
    from models.exam import Exam
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )
    from sqlalchemy import text

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="TG2",
        slug="tg2",
        domain="tg2.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="a-t6b@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="u-t6b@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    doc = Document(
        filename="d.pdf",
        original_filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    exam = Exam(title="e", created_by=user.id, institution_id=test_institution.id)
    test_db.add_all([doc, exam])
    test_db.commit()

    flags = TransferFlags(documents=True, exams=False, questions=False, tags=False)
    stats = transfer_user(test_db, user.id, target.id, flags, actor)

    assert stats.documents == 1
    assert stats.exams == 0

    test_db.refresh(doc)
    test_db.refresh(exam)
    test_db.refresh(user)
    assert user.institution_id == target.id
    assert doc.institution_id == target.id
    assert exam.institution_id == test_institution.id  # stayed


def test_transfer_zero_flags_only_moves_user(test_db, test_institution):
    """All flags False: only user moves; artifacts stay."""
    from models.auth import User, Institution
    from models.document import Document, DocumentStatus
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )
    from sqlalchemy import text

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="Z",
        slug="z",
        domain="z.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="a-zero@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="u-zero@x",
        first_name="z",
        last_name="z",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    doc = Document(
        filename="d.pdf",
        original_filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add(doc)
    test_db.commit()

    flags = TransferFlags(documents=False, exams=False, questions=False, tags=False)
    stats = transfer_user(test_db, user.id, target.id, flags, actor)

    assert stats.documents == 0
    assert stats.document_ids == []

    test_db.refresh(user)
    test_db.refresh(doc)
    assert user.institution_id == target.id
    assert doc.institution_id == test_institution.id
    assert doc.pending_reindex is False


def test_transfer_self_raises(test_db, test_institution):
    """SuperAdmin transferring themselves must fail 400 self-forbidden."""
    from models.auth import User, Institution
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
        TransferError,
    )
    from sqlalchemy import text
    import pytest

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="S",
        slug="s",
        domain="s.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="self-t6@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    test_db.add(actor)
    test_db.commit()

    flags = TransferFlags(documents=False, exams=False, questions=False, tags=False)
    with pytest.raises(TransferError) as exc:
        transfer_user(test_db, actor.id, target.id, flags, actor)
    assert exc.value.code == "admin_transfer_self_forbidden"
    assert exc.value.http_status == 400


def test_transfer_logs_audit_entry(test_db, test_institution):
    """Successful transfer creates an AuditLog row with institution_transfer metadata."""
    from models.auth import User, Institution, AuditLog
    from models.document import Document, DocumentStatus
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )
    from sqlalchemy import text
    import json

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="AUD",
        slug="aud",
        domain="aud.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="aud-admin@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="aud-user@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()
    test_db.add(
        Document(
            filename="d.pdf",
            original_filename="d.pdf",
            file_path="/tmp/d.pdf",
            file_size=100,
            mime_type="application/pdf",
            user_id=user.id,
            institution_id=test_institution.id,
            status=DocumentStatus.UPLOADED,
        )
    )
    test_db.commit()

    flags = TransferFlags(documents=True, exams=False, questions=False, tags=False)
    transfer_user(test_db, user.id, target.id, flags, actor)

    log = (
        test_db.query(AuditLog)
        .filter(AuditLog.action == "update_user")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log is not None
    # additional_data is stored as a JSON string in the AuditLog model
    meta_raw = log.additional_data
    meta = meta_raw if isinstance(meta_raw, dict) else json.loads(meta_raw or "{}")
    assert meta.get("operation") == "institution_transfer"
    assert meta.get("new_institution_id") == target.id
    assert meta.get("counts", {}).get("documents") == 1


def test_transfer_rollback_on_audit_failure(test_db, test_institution, monkeypatch):
    """If AuditService.log_action raises, transfer_user must roll back all changes."""
    from models.auth import User, Institution
    from models.document import Document, DocumentStatus
    from services import audit_service
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )
    from sqlalchemy import text
    import pytest

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="RB",
        slug="rb",
        domain="rb.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="rb-admin@x",
        first_name="r",
        last_name="a",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="rb-user@x",
        first_name="r",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    doc = Document(
        original_filename="rd.pdf",
        filename="rd.pdf",
        file_path="/tmp/rd.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add(doc)
    test_db.commit()

    # Snapshot pre-state
    original_user_iid = user.institution_id
    original_doc_iid = doc.institution_id
    original_doc_pending = doc.pending_reindex

    # Monkey-patch log_action to raise — replaces the whole method,
    # bypassing AuditService's internal try/except.
    def boom(*args, **kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr(audit_service.AuditService, "log_action", staticmethod(boom))

    flags = TransferFlags(documents=True, exams=False, questions=False, tags=False)
    with pytest.raises(RuntimeError, match="audit failure"):
        transfer_user(test_db, user.id, target.id, flags, actor)

    # After the rollback, the in-memory objects may still reflect the
    # uncommitted change; refresh from DB to confirm the actual stored state.
    test_db.expire_all()
    test_db.refresh(user)
    test_db.refresh(doc)

    assert user.institution_id == original_user_iid, (
        "User institution should have been rolled back"
    )
    assert doc.institution_id == original_doc_iid, (
        "Document institution should have been rolled back"
    )
    assert doc.pending_reindex == original_doc_pending, (
        "Document pending_reindex flag should have been rolled back"
    )

    # Verify no audit log row was committed
    from models.auth import AuditLog

    audit_count = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == "update_user",
            AuditLog.resource_id == str(user.id),
        )
        .count()
    )
    assert audit_count == 0, "No AuditLog row should exist after rollback"


def test_transfer_aborts_when_audit_returns_none(
    test_db, test_institution, monkeypatch
):
    """If AuditService.log_action returns None (production audit failure mode),
    transfer_user must raise TransferError(audit_failed) — not silently
    return success against rolled-back DB state."""
    from models.auth import User, Institution
    from models.document import Document, DocumentStatus
    from services import audit_service
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
        TransferError,
    )
    from sqlalchemy import text
    import pytest

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="AN",
        slug="an",
        domain="an.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="an-admin@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="an-user@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    doc = Document(
        original_filename="d.pdf",
        filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add(doc)
    test_db.commit()

    # Simulate AuditService's real failure mode: returns None
    def audit_returns_none(*args, **kwargs):
        return None

    monkeypatch.setattr(
        audit_service.AuditService,
        "log_action",
        staticmethod(audit_returns_none),
    )

    flags = TransferFlags(documents=True, exams=False, questions=False, tags=False)
    with pytest.raises(TransferError) as exc:
        transfer_user(test_db, user.id, target.id, flags, actor)
    assert exc.value.code == "admin_transfer_audit_failed"
    assert exc.value.http_status == 500

    # Verify state was rolled back
    test_db.expire_all()
    test_db.refresh(user)
    test_db.refresh(doc)
    assert user.institution_id == test_institution.id
    assert doc.institution_id == test_institution.id
    assert doc.pending_reindex is False


def test_transfer_preserves_global_tags(test_db, test_institution):
    """Tags with institution_id=NULL (global) must NEVER move during transfer.

    Symmetry guard against the corresponding preview test. A future refactor
    that drops the `Tag.institution_id.isnot(None)` clause from transfer_user
    would otherwise privatize all global tags into the target institution.
    """
    from models.auth import User, Institution
    from models.tag import Tag
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )
    from sqlalchemy import text

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="GT",
        slug="gt",
        domain="gt.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="gt-admin@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="gt-user@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    scoped = Tag(
        name="scoped-by-user", created_by=user.id, institution_id=test_institution.id
    )
    global_tag = Tag(
        name="global-by-user", created_by=user.id, institution_id=None
    )  # global
    test_db.add_all([scoped, global_tag])
    test_db.commit()

    flags = TransferFlags(documents=False, exams=False, questions=False, tags=True)
    stats = transfer_user(test_db, user.id, target.id, flags, actor)

    test_db.refresh(scoped)
    test_db.refresh(global_tag)
    assert scoped.institution_id == target.id, "Scoped tag should have moved"
    assert global_tag.institution_id is None, "Global tag must stay NULL"
    assert stats.tags == 1, "Only the scoped tag should count in stats"


def test_transfer_tag_only_flag(test_db, test_institution):
    """Only tags=True: only tags move; user moves too; other artifacts stay."""
    from models.auth import User, Institution
    from models.document import Document, DocumentStatus
    from models.tag import Tag
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )
    from sqlalchemy import text

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = Institution(
        name="TO",
        slug="to",
        domain="to.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(target)
    test_db.commit()

    actor = User(
        email="to-admin@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="to-user@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    doc = Document(
        original_filename="d.pdf",
        filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    tag = Tag(name="t", created_by=user.id, institution_id=test_institution.id)
    test_db.add_all([doc, tag])
    test_db.commit()

    flags = TransferFlags(documents=False, exams=False, questions=False, tags=True)
    stats = transfer_user(test_db, user.id, target.id, flags, actor)

    assert stats.documents == 0
    assert stats.tags == 1
    assert stats.document_ids == []

    test_db.refresh(doc)
    test_db.refresh(tag)
    test_db.refresh(user)
    assert user.institution_id == target.id
    assert doc.institution_id == test_institution.id  # stayed
    assert tag.institution_id == target.id


def _make_institution(test_db, name, slug):
    from models.auth import Institution

    inst = Institution(
        name=name,
        slug=slug,
        domain=f"{slug}.local",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
        is_active=True,
    )
    test_db.add(inst)
    test_db.commit()
    return inst


def test_transfer_dedups_duplicate_institution_tag(test_db, test_institution):
    """TF-369: a source tag whose name already exists (case-insensitively) in
    the target institution must NOT create a duplicate. The source tag is
    merged into the existing target tag and its question/document links are
    re-pointed onto that target tag."""
    from sqlalchemy import func, text
    from models.auth import User
    from models.document import Document, DocumentStatus
    from models.question_review import QuestionReview
    from models.tag import Tag, QuestionTag, DocumentTag
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = _make_institution(test_db, "DedupTarget", "deduptarget")

    actor = User(
        email="dedup-admin@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="dedup-user@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    # Source tag "Algebra" in the source institution, and a pre-existing
    # target tag "algebra" (different case) in the target institution.
    source_tag = Tag(
        name="Algebra", created_by=user.id, institution_id=test_institution.id
    )
    target_tag = Tag(name="algebra", created_by=actor.id, institution_id=target.id)
    test_db.add_all([source_tag, target_tag])
    test_db.commit()

    # Link the source tag to a question and a document.
    review = QuestionReview(
        question_text="q",
        question_type="single_choice",
        difficulty="easy",
        topic="t",
        created_by=user.id,
        institution_id=test_institution.id,
    )
    doc = Document(
        original_filename="d.pdf",
        filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add_all([review, doc])
    test_db.commit()
    test_db.add(QuestionTag(question_id=review.id, tag_id=source_tag.id))
    test_db.add(DocumentTag(document_id=doc.id, tag_id=source_tag.id))
    test_db.commit()

    source_tag_id = source_tag.id
    target_tag_id = target_tag.id

    flags = TransferFlags(documents=False, exams=False, questions=False, tags=True)
    stats = transfer_user(test_db, user.id, target.id, flags, actor)

    assert stats.tags == 1, "One source tag was processed"

    # Source tag is gone, target tag survives.
    assert test_db.query(Tag).filter(Tag.id == source_tag_id).first() is None
    assert test_db.query(Tag).filter(Tag.id == target_tag_id).first() is not None

    # Exactly one institution tag named "algebra" exists in the target.
    dupes = (
        test_db.query(Tag)
        .filter(
            Tag.institution_id == target.id,
            func.lower(Tag.name) == "algebra",
        )
        .count()
    )
    assert dupes == 1, "No duplicate institution tag in the target"

    # Links were re-pointed onto the surviving target tag.
    q_link = (
        test_db.query(QuestionTag).filter(QuestionTag.question_id == review.id).one()
    )
    assert q_link.tag_id == target_tag_id
    d_link = test_db.query(DocumentTag).filter(DocumentTag.document_id == doc.id).one()
    assert d_link.tag_id == target_tag_id


def test_transfer_dedup_avoids_duplicate_link(test_db, test_institution):
    """TF-369: when a question is already tagged with BOTH the source tag and
    the colliding target tag, merging must not create a duplicate
    (question_id, tag_id) link — the redundant source link is dropped."""
    from sqlalchemy import text
    from models.auth import User
    from models.question_review import QuestionReview
    from models.tag import Tag, QuestionTag
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = _make_institution(test_db, "DedupTarget2", "deduptarget2")

    actor = User(
        email="dedup2-admin@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="dedup2-user@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    source_tag = Tag(
        name="Shared", created_by=user.id, institution_id=test_institution.id
    )
    target_tag = Tag(name="shared", created_by=actor.id, institution_id=target.id)
    test_db.add_all([source_tag, target_tag])
    test_db.commit()

    review = QuestionReview(
        question_text="q",
        question_type="single_choice",
        difficulty="easy",
        topic="t",
        created_by=user.id,
        institution_id=test_institution.id,
    )
    test_db.add(review)
    test_db.commit()
    # The same question is already linked to BOTH tags.
    test_db.add(QuestionTag(question_id=review.id, tag_id=source_tag.id))
    test_db.add(QuestionTag(question_id=review.id, tag_id=target_tag.id))
    test_db.commit()

    target_tag_id = target_tag.id

    flags = TransferFlags(documents=False, exams=False, questions=False, tags=True)
    transfer_user(test_db, user.id, target.id, flags, actor)

    # Exactly one link remains for the question, pointing at the target tag.
    links = (
        test_db.query(QuestionTag).filter(QuestionTag.question_id == review.id).all()
    )
    assert len(links) == 1
    assert links[0].tag_id == target_tag_id


def test_transfer_dedup_avoids_duplicate_document_link(test_db, test_institution):
    """TF-369: the DocumentTag branch of _repoint_tag_links must drop a redundant
    link too — a document already linked to BOTH the source and colliding target
    tag must end with a single (document_id, tag_id) row. Mirrors the QuestionTag
    case so a future divergence between the two composite-PK link tables is caught.
    """
    from sqlalchemy import text
    from models.auth import User
    from models.tag import Tag, DocumentTag
    from services.user_institution_transfer_service import (
        transfer_user,
        TransferFlags,
    )

    test_db.execute(
        text(
            "SELECT setval('institutions_id_seq', "
            "GREATEST((SELECT MAX(id) FROM institutions), 1))"
        )
    )

    target = _make_institution(test_db, "DedupDocTarget", "dearmingdoctarget")

    actor = User(
        email="dedupdoc-admin@x",
        first_name="a",
        last_name="d",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
        is_superuser=True,
    )
    user = User(
        email="dedupdoc-user@x",
        first_name="u",
        last_name="u",
        password_hash="x",
        institution_id=test_institution.id,
        status="active",
    )
    test_db.add_all([actor, user])
    test_db.commit()

    source_tag = Tag(
        name="Shared", created_by=user.id, institution_id=test_institution.id
    )
    target_tag = Tag(name="shared", created_by=actor.id, institution_id=target.id)
    test_db.add_all([source_tag, target_tag])
    test_db.commit()

    doc = Document(
        original_filename="d.pdf",
        filename="d.pdf",
        file_path="/tmp/d.pdf",
        file_size=100,
        mime_type="application/pdf",
        user_id=user.id,
        institution_id=test_institution.id,
        status=DocumentStatus.UPLOADED,
    )
    test_db.add(doc)
    test_db.commit()
    # The same document is already linked to BOTH tags.
    test_db.add(DocumentTag(document_id=doc.id, tag_id=source_tag.id))
    test_db.add(DocumentTag(document_id=doc.id, tag_id=target_tag.id))
    test_db.commit()

    target_tag_id = target_tag.id

    flags = TransferFlags(documents=False, exams=False, questions=False, tags=True)
    transfer_user(test_db, user.id, target.id, flags, actor)

    links = test_db.query(DocumentTag).filter(DocumentTag.document_id == doc.id).all()
    assert len(links) == 1
    assert links[0].tag_id == target_tag_id
