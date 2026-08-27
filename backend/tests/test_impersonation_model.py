"""Unit tests for the ImpersonationSession model + AuditLog.impersonator_user_id
(TF-740, part of the TF-739 impersonation epic).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from models.auth import AuditLog, ImpersonationSession, Institution, User, UserStatus


def _make_institution(db, slug: str = "impersonation-model-test") -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db, inst: Institution, email: str) -> User:
    user = User(
        email=email,
        password_hash="dummy",  # pragma: allowlist secret
        first_name="Test",
        last_name="User",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def test_impersonation_session_persists_with_relationships(test_db):
    inst = _make_institution(test_db)
    admin = _make_user(test_db, inst, "admin@impersonation-model-test.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-test.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason="Support-Anfrage TICKET-123",
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    assert session.id is not None
    assert session.started_at is not None
    assert session.ended_at is None
    assert session.end_reason is None
    assert session.admin_user.id == admin.id
    assert session.target_user.id == target.id


def test_impersonation_session_can_be_ended(test_db):
    inst = _make_institution(test_db, slug="impersonation-model-end")
    admin = _make_user(test_db, inst, "admin@impersonation-model-end.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-end.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason="Bug reproduzieren",
    )
    test_db.add(session)
    test_db.flush()

    session.end("manual")
    test_db.commit()
    test_db.refresh(session)

    assert session.ended_at is not None
    assert session.end_reason == "manual"


def test_impersonation_session_end_rejects_double_end(test_db):
    inst = _make_institution(test_db, slug="impersonation-model-double-end")
    admin = _make_user(test_db, inst, "admin@impersonation-model-double-end.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-double-end.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target.id, reason="x"
    )
    test_db.add(session)
    test_db.flush()

    session.end("manual")
    with pytest.raises(ValueError):
        session.end("timeout")


def test_impersonation_session_end_rejects_invalid_reason(test_db):
    inst = _make_institution(test_db, slug="impersonation-model-bad-end-reason")
    admin = _make_user(test_db, inst, "admin@impersonation-model-bad-end-reason.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-bad-end-reason.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target.id, reason="x"
    )
    test_db.add(session)
    test_db.flush()

    with pytest.raises(ValueError):
        session.end("banana")
    # end() raised before touching either field — session is still active.
    assert session.ended_at is None
    assert session.end_reason is None


def test_impersonation_session_rejects_self_impersonation(test_db):
    inst = _make_institution(test_db, slug="impersonation-model-self")
    admin = _make_user(test_db, inst, "admin@impersonation-model-self.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=admin.id, reason="x"
    )
    test_db.add(session)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_impersonation_session_rejects_invalid_end_reason_at_db_level(test_db):
    # Bypasses end() to prove the CHECK constraint itself (not just the
    # model method) rejects an out-of-vocabulary end_reason.
    inst = _make_institution(test_db, slug="impersonation-model-db-end-reason")
    admin = _make_user(test_db, inst, "admin@impersonation-model-db-end-reason.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-db-end-reason.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason="x",
        ended_at=datetime.now(timezone.utc),
        end_reason="banana",
    )
    test_db.add(session)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_impersonation_session_rejects_half_ended_state(test_db):
    # ended_at set without end_reason (or vice versa) must be rejected by
    # the ck_impersonation_sessions_end_pairing CHECK constraint.
    inst = _make_institution(test_db, slug="impersonation-model-half-ended")
    admin = _make_user(test_db, inst, "admin@impersonation-model-half-ended.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-half-ended.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id,
        target_user_id=target.id,
        reason="x",
        ended_at=datetime.now(timezone.utc),
        end_reason=None,
    )
    test_db.add(session)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_impersonation_session_enforces_one_active_session_per_admin(test_db):
    inst = _make_institution(test_db, slug="impersonation-model-one-active")
    admin = _make_user(test_db, inst, "admin@impersonation-model-one-active.ch")
    target_a = _make_user(test_db, inst, "target-a@impersonation-model-one-active.ch")
    target_b = _make_user(test_db, inst, "target-b@impersonation-model-one-active.ch")

    first = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target_a.id, reason="x"
    )
    test_db.add(first)
    test_db.commit()

    # Same admin, still active — no nested impersonation allowed (TF-739).
    second = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target_b.id, reason="y"
    )
    test_db.add(second)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()

    # Ending the first session frees the admin up to start a new one.
    test_db.refresh(first)
    first.end("manual")
    test_db.commit()

    third = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target_b.id, reason="z"
    )
    test_db.add(third)
    test_db.commit()
    test_db.refresh(third)
    assert third.id is not None


def test_impersonation_session_survives_admin_deletion(test_db):
    # ImpersonationSession is an audit trail — deleting a user who was once
    # an admin in a session must not fail; the row survives with a NULL
    # admin_user_id instead (see the nullable=True + ondelete="SET NULL"
    # rationale in the model docstring).
    inst = _make_institution(test_db, slug="impersonation-model-admin-delete")
    admin = _make_user(test_db, inst, "admin@impersonation-model-admin-delete.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-admin-delete.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target.id, reason="x"
    )
    test_db.add(session)
    test_db.commit()
    session_id = session.id

    test_db.delete(admin)
    test_db.commit()

    persisted = test_db.get(ImpersonationSession, session_id)
    assert persisted is not None
    assert persisted.admin_user_id is None
    assert persisted.target_user_id == target.id


def test_impersonation_session_survives_target_deletion(test_db):
    inst = _make_institution(test_db, slug="impersonation-model-target-delete")
    admin = _make_user(test_db, inst, "admin@impersonation-model-target-delete.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-target-delete.ch")

    session = ImpersonationSession(
        admin_user_id=admin.id, target_user_id=target.id, reason="x"
    )
    test_db.add(session)
    test_db.commit()
    session_id = session.id

    test_db.delete(target)
    test_db.commit()

    persisted = test_db.get(ImpersonationSession, session_id)
    assert persisted is not None
    assert persisted.admin_user_id == admin.id
    assert persisted.target_user_id is None


def test_audit_log_impersonator_user_id_is_nullable_and_optional(test_db):
    inst = _make_institution(test_db, slug="impersonation-model-audit")
    target = _make_user(test_db, inst, "target@impersonation-model-audit.ch")

    # No impersonator set — regular, non-impersonated action.
    log = AuditLog(
        user_id=target.id,
        action="question.create",
        status="success",
    )
    test_db.add(log)
    test_db.commit()
    test_db.refresh(log)

    assert log.impersonator_user_id is None


def test_audit_log_impersonator_user_id_references_admin(test_db):
    inst = _make_institution(test_db, slug="impersonation-model-audit-imp")
    admin = _make_user(test_db, inst, "admin@impersonation-model-audit-imp.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-audit-imp.ch")

    log = AuditLog(
        user_id=target.id,
        impersonator_user_id=admin.id,
        action="question.create",
        status="success",
    )
    test_db.add(log)
    test_db.commit()
    test_db.refresh(log)

    assert log.impersonator_user_id == admin.id
    assert log.impersonator.id == admin.id
    # user_id (and the `user` relationship) must keep pointing at the
    # target, not the impersonator — this is the whole point of keeping the
    # two FKs disambiguated (see the comment on AuditLog.impersonator_user_id).
    assert log.user_id == target.id
    assert log.user.id == target.id
    # The impersonator must NOT show up in their own `audit_logs` for an
    # action they only impersonated, not performed as themselves.
    test_db.refresh(admin)
    assert log not in admin.audit_logs
    test_db.refresh(target)
    assert log in target.audit_logs


def test_audit_log_impersonator_user_id_survives_admin_deletion(test_db):
    # Same SET NULL-survives-deletion contract as ImpersonationSession
    # itself: the audit row must not vanish (or block the delete) just
    # because the impersonating admin was later removed.
    inst = _make_institution(test_db, slug="impersonation-model-audit-imp-delete")
    admin = _make_user(test_db, inst, "admin@impersonation-model-audit-imp-delete.ch")
    target = _make_user(test_db, inst, "target@impersonation-model-audit-imp-delete.ch")

    log = AuditLog(
        user_id=target.id,
        impersonator_user_id=admin.id,
        action="question.create",
        status="success",
    )
    test_db.add(log)
    test_db.commit()
    log_id = log.id

    test_db.delete(admin)
    test_db.commit()

    persisted = test_db.get(AuditLog, log_id)
    assert persisted is not None
    assert persisted.impersonator_user_id is None
    assert persisted.user_id == target.id
