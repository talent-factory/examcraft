"""Regression test for tasks.session_cleanup.cleanup_old_sessions.

``cleanup_old_sessions`` used to filter with ``not UserSession.is_active``,
which Python evaluates to the literal ``False`` before SQLAlchemy ever sees
it -- the compiled query was ``WHERE false AND revoked_at < :cutoff``, so the
delete matched zero rows on every run, forever, while still logging a
successful-looking "Deleted 0 old sessions". This asserts a non-zero delete
count for a fixture-seeded old, inactive session, so reverting the fix (back
to the bare ``not`` form) makes this test fail rather than pass vacuously --
the same class of bug, and the same style of regression guard, as
``test_rbac_service.py::test_list_roles_excluding_system_roles_returns_the_custom_ones``
in TF-660.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from models.auth import Institution, User, UserSession, UserStatus
from tasks.session_cleanup import cleanup_old_sessions


def _institution(db) -> Institution:
    inst = Institution(
        name="session-cleanup-inst",
        slug="session-cleanup-test",
        subscription_tier="free",
        max_users=10,
        max_documents=10,
        max_questions_per_month=10,
    )
    db.add(inst)
    db.flush()
    return inst


def _user(db, inst: Institution, email: str) -> User:
    user = User(
        email=email,
        password_hash="dummy",
        first_name="S",
        last_name="U",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def _session(
    db,
    user: User,
    *,
    token_jti: str,
    is_active: bool,
    revoked_at: datetime | None,
) -> int:
    session = UserSession(
        user_id=user.id,
        token_jti=token_jti,
        is_active=is_active,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at=revoked_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session.id


def test_cleanup_old_sessions_deletes_old_inactive_sessions_only(test_db):
    """Only sessions that are BOTH inactive AND revoked past the cutoff are
    deleted. An active-but-old session and a recently-revoked session must
    survive -- proving the query's two conditions are actually ANDed
    together, not silently short-circuited to "match nothing"."""
    inst = _institution(test_db)
    user = _user(test_db, inst, "session-cleanup@test.ch")

    now = datetime.now(timezone.utc)
    old_revoked = now - timedelta(days=45)
    recent_revoked = now - timedelta(days=2)

    old_inactive_id = _session(
        test_db,
        user,
        token_jti="jti-old-inactive",
        is_active=False,
        revoked_at=old_revoked,
    )
    recent_inactive_id = _session(
        test_db,
        user,
        token_jti="jti-recent-inactive",
        is_active=False,
        revoked_at=recent_revoked,
    )
    # Still active, but revoked_at happens to be old (e.g. a stale/incorrect
    # write elsewhere) -- must NOT be deleted while is_active is True.
    active_but_old_id = _session(
        test_db,
        user,
        token_jti="jti-active-old",
        is_active=True,
        revoked_at=old_revoked,
    )

    with (
        patch("tasks.session_cleanup.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        deleted_count = cleanup_old_sessions(days=30)

    assert deleted_count == 1
    remaining_ids = {
        row.id
        for row in test_db.query(UserSession)
        .filter(
            UserSession.id.in_([old_inactive_id, recent_inactive_id, active_but_old_id])
        )
        .all()
    }
    assert old_inactive_id not in remaining_ids
    assert recent_inactive_id in remaining_ids
    assert active_but_old_id in remaining_ids


def test_cleanup_old_sessions_returns_zero_when_nothing_qualifies(test_db):
    inst = _institution(test_db)
    user = _user(test_db, inst, "session-cleanup-empty@test.ch")
    _session(
        test_db,
        user,
        token_jti="jti-active-fresh",
        is_active=True,
        revoked_at=None,
    )

    with (
        patch("tasks.session_cleanup.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
    ):
        deleted_count = cleanup_old_sessions(days=30)

    assert deleted_count == 0
