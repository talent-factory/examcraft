"""Server-side sessions (EXAMCRAFT-125, BFF pattern).

The cookie carries an opaque 256-bit random token; ``auth_sessions`` stores
only its SHA-256 hash. Sessions have an absolute lifetime (14 days for a
login, a short window for impersonation) and are never extended. Logout
ends only the local session.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.auth import AuthSession, User, UserStatus

SESSION_COOKIE_NAME = "session_id"
# Second cookie, only present while impersonating. It is worthless on its
# own: it only counts together with a valid login session of the admin.
IMPERSONATION_COOKIE_NAME = "impersonation_id"
SESSION_MAX_AGE = timedelta(days=14)
# Hard cap of an impersonation session, same value as the former token (TF-741).
IMPERSONATION_SESSION_MAX_AGE = timedelta(minutes=30)
# Starting an impersonation requires an IdP authentication (``auth_time``) at
# most this old (replaces the former password step-up, there is no local
# password anymore).
REAUTH_MAX_AGE = timedelta(minutes=10)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def create_session(
    db: Session,
    user_id: int,
    *,
    max_age: timedelta = SESSION_MAX_AGE,
    impersonator_id: Optional[int] = None,
    impersonation_session_id: Optional[int] = None,
    authenticated_at: Optional[datetime] = None,
    commit: bool = True,
) -> tuple[str, AuthSession]:
    """Create a session and return ``(cookie_token, row)``."""
    token = secrets.token_urlsafe(32)
    row = AuthSession(
        token_hash=_hash(token),
        user_id=user_id,
        impersonator_id=impersonator_id,
        impersonation_session_id=impersonation_session_id,
        authenticated_at=authenticated_at,
        expires_at=datetime.now(timezone.utc) + max_age,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return token, row


def get_active_session(db: Session, token: Optional[str]) -> Optional[AuthSession]:
    """The valid session for a cookie token, or ``None``. Expired rows are deleted."""
    if not token:
        return None
    row = db.query(AuthSession).filter(AuthSession.token_hash == _hash(token)).first()
    if row is None:
        return None
    if _aware(row.expires_at) <= datetime.now(timezone.utc):
        db.delete(row)
        db.commit()
        return None
    return row


def resolve_effective_session(
    db: Session, token: Optional[str], impersonation_token: Optional[str]
) -> Optional[AuthSession]:
    """The session a request acts as.

    The login session must be valid. If an impersonation cookie is present
    and its session belongs to the same admin, the request acts as the
    impersonated user. An expired or foreign impersonation cookie is
    ignored, so the admin falls back to their own identity.
    """
    base = get_active_session(db, token)
    # An impersonation session is never a valid login session: otherwise its
    # cookie, copied into ``session_id``, would skip the admin checks below.
    if base is None or base.impersonator_id is not None:
        return None
    if impersonation_token:
        imp = get_active_session(db, impersonation_token)
        if (
            imp is not None
            and imp.impersonation_session_id is not None
            and imp.impersonator_id == base.user_id
        ):
            if impersonator_still_allowed(db, imp):
                return imp
            # The admin was suspended or lost the permission meanwhile: the
            # impersonation must not outlive that (up to 30 minutes).
            db.delete(imp)
            db.commit()
    return base


def impersonator_still_allowed(db: Session, row: AuthSession) -> bool:
    """The admin behind an impersonation session is still active and may impersonate."""
    admin = db.get(User, row.impersonator_id)
    return (
        admin is not None
        and admin.status == UserStatus.ACTIVE.value
        and admin.has_permission("users:impersonate")
    )


def delete_session(db: Session, token: Optional[str]) -> None:
    """Idempotent: an unknown token is a no-op."""
    if not token:
        return
    row = db.query(AuthSession).filter(AuthSession.token_hash == _hash(token)).first()
    if row is not None:
        db.delete(row)
        db.commit()


def delete_impersonation_sessions(db: Session, impersonation_session_id: int) -> int:
    """End the login session(s) of an impersonation session. Caller commits."""
    return (
        db.query(AuthSession)
        .filter(AuthSession.impersonation_session_id == impersonation_session_id)
        .delete(synchronize_session=False)
    )


def is_recent_login(row: AuthSession) -> bool:
    """True if the user authenticated at the IdP within ``REAUTH_MAX_AGE``.

    Based on the IdP's ``auth_time``, never on the session age. Without a
    recorded ``auth_time`` there is no proof, so the answer is False.
    """
    if row.authenticated_at is None:
        return False
    return datetime.now(timezone.utc) - _aware(row.authenticated_at) <= REAUTH_MAX_AGE


def purge_expired(db: Session) -> int:
    """Delete expired sessions (for a periodic sweep). Commits."""
    count = (
        db.query(AuthSession)
        .filter(AuthSession.expires_at <= datetime.now(timezone.utc))
        .delete(synchronize_session=False)
    )
    db.commit()
    return count
