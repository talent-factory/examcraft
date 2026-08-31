"""
Authentication Service für ExamCraft AI
JWT Token Generation, Validation, Refresh Token Logic
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from fastapi import Request
from sqlalchemy.orm import Session
import secrets
import logging

from models.auth import ImpersonationSession, User, UserSession, UserStatus
from services.audit_service import AuditService
from services.redis_service import SessionStore, TokenBlacklist

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    _env = os.getenv("ENVIRONMENT", "development")
    _mode = os.getenv("DEPLOYMENT_MODE", "core")
    if _env == "production" or _mode == "full":
        raise RuntimeError(
            "FATAL: JWT_SECRET_KEY muss in Produktion gesetzt sein. "
            "Start mit unsicherem Default verweigert."
        )
    logger.warning(
        "JWT_SECRET_KEY nicht gesetzt! Verwende unsicheren Default. "
        "Dies ist nur in der Entwicklung akzeptabel."
    )
    SECRET_KEY = (
        "insecure-dev-default-do-not-use-in-production"  # pragma: allowlist secret
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# TF-741: impersonation access tokens are hard-capped at 30 minutes —
# deliberately NOT driven by an env var, since this is a security
# invariant of the impersonation feature, not a deployment setting.
IMPERSONATION_TOKEN_EXPIRE_MINUTES = 30


class AuthService:
    """
    Authentication Service für JWT Token Management
    """

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise. Also False -- not a
            raised exception -- for a malformed/corrupted hash or an
            unencodable password (TF-758 review fix): callers on
            security-sensitive paths (login, impersonation step-up) build
            audit trails and lockout counters around this check, and a
            bcrypt ``ValueError``/``UnicodeEncodeError`` bubbling up past
            them as an unhandled 500 would skip both. Failing closed here
            makes any such error behave exactly like a wrong password.
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
                if isinstance(hashed_password, str)
                else hashed_password,
            )
        except (ValueError, TypeError, UnicodeEncodeError, UnicodeDecodeError):
            logger.exception("verify_password: malformed password or password hash")
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def create_access_token(
        data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token

        Args:
            data: Data to encode in token (user_id, email, etc.)
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )

        # Add standard JWT claims
        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "jti": secrets.token_urlsafe(32),  # JWT ID for token revocation
            }
        )

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token

        Args:
            data: Data to encode in token (user_id, email, etc.)
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=REFRESH_TOKEN_EXPIRE_DAYS
            )

        # Add standard JWT claims
        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "jti": secrets.token_urlsafe(32),  # JWT ID for token revocation
                "type": "refresh",  # Mark as refresh token
            }
        )

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token

        Args:
            token: JWT token to decode

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None

    @staticmethod
    def create_tokens_for_user(
        user: User,
        db: Session,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user and store session

        Args:
            user: User object
            db: Database session
            user_agent: User agent string
            ip_address: IP address

        Returns:
            Dictionary with access_token and refresh_token
        """
        # Create token data
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "institution_id": user.institution_id,
            "roles": [role.name for role in user.roles],
        }

        # Create tokens
        access_token = AuthService.create_access_token(token_data)
        refresh_token = AuthService.create_refresh_token(token_data)

        # Decode tokens to get JTI
        access_payload = AuthService.decode_token(access_token)
        refresh_payload = AuthService.decode_token(refresh_token)

        if not access_payload or not refresh_payload:
            raise ValueError("Failed to decode tokens")

        # Create session record in database
        session = UserSession(
            user_id=user.id,
            token_jti=access_payload["jti"],
            refresh_token_jti=refresh_payload["jti"],
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.fromtimestamp(refresh_payload["exp"]),
            is_active=True,
        )

        db.add(session)
        db.commit()

        # Also store session in Redis for fast lookup
        try:
            session_store = SessionStore()
            ttl_seconds = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            session_store.create_session(
                session_id=refresh_payload["jti"],
                user_id=user.id,
                data={
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "access_token_jti": access_payload["jti"],
                },
                ttl_seconds=ttl_seconds,
            )
        except Exception as e:
            logger.warning(f"Failed to create Redis session: {str(e)}")

        logger.info(f"Created tokens for user {user.email} (ID: {user.id})")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def create_impersonation_token(
        target_user: User,
        db: Session,
        impersonator_id: int,
        impersonation_session_id: int,
    ) -> Dict[str, Any]:
        """Create an access token for impersonating ``target_user`` (TF-741).

        Deliberately mints an ACCESS TOKEN ONLY — no refresh token. Issuing
        a refresh token here would let the shared ``/auth/refresh`` endpoint
        mint a fresh access token for the target user without the
        ``impersonator_id``/``impersonation_session_id`` claims and without
        the 30-minute cap, silently turning a time-boxed support session
        into a permanent, unflagged session as the target user. Once this
        token expires, the normal 401 path applies; there is no renewal.

        Args:
            target_user: The user being impersonated (token is issued "as" them)
            db: Database session
            impersonator_id: ID of the admin performing the impersonation
            impersonation_session_id: ID of the ``ImpersonationSession`` row

        Returns:
            Dictionary with ``access_token``, ``token_type``, ``expires_in``
        """
        token_data = {
            "sub": str(target_user.id),
            "email": target_user.email,
            "institution_id": target_user.institution_id,
            "roles": [role.name for role in target_user.roles],
            "impersonator_id": impersonator_id,
            "impersonation_session_id": impersonation_session_id,
        }

        access_token = AuthService.create_access_token(
            token_data,
            expires_delta=timedelta(minutes=IMPERSONATION_TOKEN_EXPIRE_MINUTES),
        )
        access_payload = AuthService.decode_token(access_token)

        if not access_payload:
            raise ValueError("Failed to decode impersonation access token")

        # No refresh_token_jti: this session is not refreshable (see above).
        session = UserSession(
            user_id=target_user.id,
            token_jti=access_payload["jti"],
            refresh_token_jti=None,
            expires_at=datetime.fromtimestamp(access_payload["exp"]),
            is_active=True,
        )
        db.add(session)
        db.commit()

        logger.info(
            f"Created impersonation token for user {target_user.email} "
            f"(ID: {target_user.id}) by admin ID {impersonator_id} "
            f"(session ID: {impersonation_session_id})"
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": IMPERSONATION_TOKEN_EXPIRE_MINUTES * 60,
        }

    # TF-758: shared with the impersonation step-up in api/admin.py so that
    # repeatedly guessing an account's own password through *either* surface
    # locks the same account. Same thresholds as POST /auth/login (kept as
    # its own inline copy there -- see auth.py's `login()` -- so this change
    # doesn't touch that already-tested flow); both surfaces read/write the
    # same `failed_login_attempts`/`last_failed_login` columns, so a lockout
    # triggered from one blocks the other too.
    MAX_FAILED_PASSWORD_ATTEMPTS = 10
    PASSWORD_LOCKOUT_DURATION_SECONDS = 30 * 60  # 30 minutes

    @staticmethod
    def is_locked_out(user: User) -> bool:
        """True if ``user`` is currently locked out of re-proving their own
        password (TF-758), e.g. via the impersonation step-up."""
        if (user.failed_login_attempts or 0) < AuthService.MAX_FAILED_PASSWORD_ATTEMPTS:
            return False
        if user.last_failed_login is None:
            return False
        elapsed = (datetime.now(timezone.utc) - user.last_failed_login).total_seconds()
        return elapsed < AuthService.PASSWORD_LOCKOUT_DURATION_SECONDS

    @staticmethod
    def record_failed_own_password_attempt(user: User, db: Session) -> None:
        """Increment the shared failed-attempt counter after ``user`` gets
        their own password wrong (TF-758). Committed immediately and
        separately from any audit write -- mirrors POST /auth/login's
        pattern -- so a later audit-log failure can't roll this back."""
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        user.last_failed_login = datetime.now(timezone.utc)
        try:
            db.commit()
        except Exception:
            logger.exception(
                "Failed to persist failed-password-attempt counter for user %s",
                user.id,
            )
            db.rollback()

    @staticmethod
    def reset_failed_own_password_attempts(user: User, db: Session) -> None:
        """Clear the shared failed-attempt counter after ``user`` proves
        their own password again (TF-758), mirroring the reset on a
        successful POST /auth/login."""
        if not user.failed_login_attempts and user.last_failed_login is None:
            return  # nothing to reset -- avoid a no-op commit on every step-up
        user.failed_login_attempts = 0
        user.last_failed_login = None
        try:
            db.commit()
        except Exception:
            logger.exception(
                "Failed to reset failed-password-attempt counter for user %s",
                user.id,
            )
            db.rollback()

    @staticmethod
    def record_impersonation_started(
        db: Session,
        *,
        admin_user_id: int,
        target_user_id: int,
        session_id: int,
        reason: str,
        started_at: Optional[datetime] = None,
        request: Optional[Request] = None,
    ) -> None:
        """Audit + notify when an ``ImpersonationSession`` begins (TF-742
        audit, TF-759 real-time notify). Symmetric counterpart of
        ``record_impersonation_ended`` below -- same "audit event, then a
        best-effort email to the target" shape, this time fired at the
        start of the session instead of its end, so the target learns
        about an ongoing session without waiting for it to close.

        Called from ``start_impersonation`` while still on the admin's own,
        not-yet-impersonated request -- the request-scoped
        ``ImpersonationContext`` isn't set yet at that point (it only
        starts applying to the *next* request, the one authenticated with
        the freshly-minted impersonation token), so
        ``impersonator_user_id`` has to be passed explicitly instead of
        relying on ``AuditService.log_action``'s auto-fill.

        Never raises: called on the admin's own request right after the
        impersonation token has already been minted and returned to the
        caller, so a failure here (audit write, a DB hiccup on the lookups
        below, a Celery broker outage) must never turn an already-granted
        session into a 500 for the admin. ``log_event_best_effort`` already
        swallows audit-write failures; the ``db.get()`` lookups through the
        notification dispatch are wrapped in their own try/except for the
        same reason, and logged the same way (``logger.error`` with
        ``exc_info=True`` and all three correlating IDs), mirroring the
        review fix already applied to ``record_impersonation_ended`` below.
        """
        AuditService.log_event_best_effort(
            db,
            action=AuditService.ACTION_IMPERSONATION_START,
            user_id=target_user_id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=target_user_id,
            additional_data={
                "reason": reason,
                "impersonation_session_id": session_id,
            },
            impersonator_user_id=admin_user_id,
            request=request,
        )

        try:
            target = db.get(User, target_user_id)
            admin = db.get(User, admin_user_id)
            if target is None or admin is None:
                return

            from tasks.notification_tasks import send_impersonation_started_email

            send_impersonation_started_email.delay(
                to_email=target.email,
                to_name=target.first_name or target.email,
                admin_name=admin.full_name or admin.email,
                reason=reason,
                started_at=started_at.isoformat() if started_at else None,
            )
        except Exception:
            logger.error(
                "Failed to dispatch impersonation-started email (session %s, "
                "admin %s, target %s)",
                session_id,
                admin_user_id,
                target_user_id,
                exc_info=True,
            )

    @staticmethod
    def record_impersonation_ended(
        db: Session,
        *,
        admin_user_id: Optional[int],
        target_user_id: Optional[int],
        session_id: int,
        reason: Optional[str],
        started_at: Optional[datetime],
        ended_at: Optional[datetime],
        end_reason: str,
        request: Optional[Request] = None,
    ) -> None:
        """Audit + notify once an ``ImpersonationSession`` is durably closed
        (TF-742). Shared by the manual end endpoint, its lost-token
        fallback, ``POST /auth/logout`` while impersonating, and the
        timeout reaper -- one place so all four paths behave identically.

        Never raises: called after the session-closing UPDATE has already
        committed, so a failure here (audit write, missing user rows, a DB
        hiccup on the lookups below, a Celery broker outage) must never
        unwind or fail that request. ``log_event_best_effort`` already
        swallows audit-write failures; everything from the ``db.get()``
        lookups through the notification dispatch is wrapped in its own
        try/except for the same reason (review fix: the two lookups used to
        sit *outside* that guard, so a DB-level error there -- e.g. a
        dropped connection -- would have propagated past this "never
        raises" contract and turned an already-successful session-close
        into a 500 for the caller).
        """
        AuditService.log_event_best_effort(
            db,
            action=AuditService.ACTION_IMPERSONATION_END,
            user_id=target_user_id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=target_user_id,
            additional_data={
                "reason": reason,
                "impersonation_session_id": session_id,
                "ended_at": ended_at.isoformat() if ended_at else None,
                "end_reason": end_reason,
            },
            impersonator_user_id=admin_user_id,
            request=request,
        )

        # ondelete="SET NULL" on both FKs: the admin or target row may
        # already be gone (e.g. GDPR erasure) by the time this runs.
        # Nothing to notify and no one left to attribute it to.
        if target_user_id is None or admin_user_id is None:
            return

        try:
            target = db.get(User, target_user_id)
            admin = db.get(User, admin_user_id)
            if target is None or admin is None:
                return

            from tasks.notification_tasks import send_impersonation_ended_email

            send_impersonation_ended_email.delay(
                to_email=target.email,
                to_name=target.first_name or target.email,
                admin_name=admin.full_name or admin.email,
                reason=reason,
                started_at=started_at.isoformat() if started_at else None,
                ended_at=ended_at.isoformat() if ended_at else None,
                end_reason=end_reason,
            )
        except Exception:
            logger.error(
                "Failed to dispatch impersonation-ended email (session %s, "
                "admin %s, target %s)",
                session_id,
                admin_user_id,
                target_user_id,
                exc_info=True,
            )

    @staticmethod
    def end_impersonation_session(
        impersonation_session_id: int,
        token_jti: str,
        db: Session,
        request: Optional[Request] = None,
    ) -> Dict[str, bool]:
        """Atomically close an ``ImpersonationSession`` row and revoke its
        token (TF-741 review fix).

        Used both by ``POST /admin/impersonate/end`` (impersonation token
        still present) and by ``POST /auth/logout`` called while
        impersonating, where logging out must end the impersonation rather
        than revoke the real target user's other sessions.

        The session UPDATE is conditioned on ``ended_at IS NULL`` at write
        time (not just checked via an earlier SELECT), so it can never
        clobber a concurrent close by the reaper
        (``tasks.maintenance_tasks.reap_stuck_impersonation_sessions``) or
        another request racing on the same session — whichever write
        commits first wins; the loser's UPDATE matches zero rows instead of
        overwriting the winner's ``end_reason``.

        Returns ``{"session_closed": ..., "token_revoked": ...}`` so the
        caller can log when either step found nothing to do. The row is
        read once *before* the conditional UPDATE below so the TF-742 audit
        + email side effects have ``reason``/``admin_user_id``/
        ``target_user_id`` to work with -- those columns are immutable
        once the session is created, so pre-reading them is race-safe; only
        ``updated_rows > 0`` decides whether *this* call actually won the
        race and gets to fire the side effects at all.
        """
        session_row = (
            db.query(ImpersonationSession)
            .filter(ImpersonationSession.id == impersonation_session_id)
            .first()
        )
        ended_at = datetime.now(timezone.utc)
        updated_rows = (
            db.query(ImpersonationSession)
            .filter(
                ImpersonationSession.id == impersonation_session_id,
                ImpersonationSession.ended_at.is_(None),
            )
            .update(
                {"ended_at": ended_at, "end_reason": "manual"},
                synchronize_session=False,
            )
        )
        db.commit()

        token_revoked = AuthService.revoke_token(token_jti, db)

        if updated_rows > 0 and session_row is not None:
            AuthService.record_impersonation_ended(
                db,
                admin_user_id=session_row.admin_user_id,
                target_user_id=session_row.target_user_id,
                session_id=session_row.id,
                reason=session_row.reason,
                started_at=session_row.started_at,
                ended_at=ended_at,
                end_reason="manual",
                request=request,
            )

        return {"session_closed": updated_rows > 0, "token_revoked": token_revoked}

    @staticmethod
    def end_own_impersonation_session(
        admin_user_id: int, db: Session, request: Optional[Request] = None
    ) -> Optional[int]:
        """Close the admin's own still-open impersonation session, if any.

        Fallback for ``POST /admin/impersonate/end`` when it's called with
        the admin's *own* token instead of the (lost) impersonation token —
        e.g. the impersonation tab was closed, storage was cleared, or the
        browser crashed before the admin could return normally. Without
        this, ``already_active_own_session`` in ``start_impersonation``
        would otherwise lock the admin out of impersonating anyone else
        until the reaper ages the row out (up to ~30 minutes), with no
        self-service recovery (TF-741 review fix).

        The impersonation token itself is not revoked here — it isn't known
        to this code path, which is the whole reason this fallback exists —
        but it still expires normally via its own ``exp`` claim.

        Returns the closed session's id, or ``None`` if the admin had no
        open session (or it was already closed by something else in the
        gap between the lookup and the conditional update below).
        """
        session = (
            db.query(ImpersonationSession)
            .filter(
                ImpersonationSession.admin_user_id == admin_user_id,
                ImpersonationSession.ended_at.is_(None),
            )
            .first()
        )
        if session is None:
            return None

        ended_at = datetime.now(timezone.utc)
        updated_rows = (
            db.query(ImpersonationSession)
            .filter(
                ImpersonationSession.id == session.id,
                ImpersonationSession.ended_at.is_(None),
            )
            .update(
                {"ended_at": ended_at, "end_reason": "manual"},
                synchronize_session=False,
            )
        )
        db.commit()

        if updated_rows > 0:
            AuthService.record_impersonation_ended(
                db,
                admin_user_id=session.admin_user_id,
                target_user_id=session.target_user_id,
                session_id=session.id,
                reason=session.reason,
                started_at=session.started_at,
                ended_at=ended_at,
                end_reason="manual",
                request=request,
            )

        return session.id if updated_rows > 0 else None

    @staticmethod
    def refresh_access_token(
        refresh_token: str,
        db: Session,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """
        Refresh an access token using a refresh token

        Args:
            refresh_token: Refresh token
            db: Database session
            user_agent: User agent string
            ip_address: IP address

        Returns:
            Dictionary with new access_token or None if invalid
        """
        # Decode refresh token
        payload = AuthService.decode_token(refresh_token)

        if not payload:
            logger.warning("Invalid refresh token")
            return None

        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            logger.warning("Token is not a refresh token")
            return None

        # Check if session exists and is active
        session = (
            db.query(UserSession)
            .filter(
                UserSession.refresh_token_jti == payload["jti"], UserSession.is_active
            )
            .first()
        )

        if not session:
            logger.warning(f"Session not found or inactive for JTI: {payload['jti']}")
            return None

        # Check if session is expired
        if session.expires_at < datetime.now(timezone.utc):
            logger.warning(f"Session expired for user {session.user_id}")
            session.is_active = False
            db.commit()
            return None

        # Get user
        user = db.query(User).filter(User.id == session.user_id).first()

        if not user or user.status != UserStatus.ACTIVE.value:
            logger.warning(f"User not found or inactive: {session.user_id}")
            return None

        # Create new access token and refresh token (Token Rotation)
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "institution_id": user.institution_id,
            "roles": [role.name for role in user.roles],
        }

        access_token = AuthService.create_access_token(token_data)
        access_payload = AuthService.decode_token(access_token)

        if not access_payload:
            raise ValueError("Failed to decode new access token")

        # Create new refresh token (Token Rotation for security)
        new_refresh_token = AuthService.create_refresh_token(token_data)
        refresh_payload = AuthService.decode_token(new_refresh_token)

        if not refresh_payload:
            raise ValueError("Failed to decode new refresh token")

        # Update session with new token JTIs
        session.token_jti = access_payload["jti"]
        session.refresh_token_jti = refresh_payload["jti"]
        session.last_activity_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"Refreshed tokens for user {user.email} (ID: {user.id})")

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def revoke_token(token_jti: str, db: Session, ttl_seconds: int = 1800) -> bool:
        """
        Revoke a token by marking its session as inactive

        Args:
            token_jti: JWT ID of token to revoke
            db: Database session
            ttl_seconds: Time until token expires naturally (for Redis blacklist)

        Returns:
            True if token was revoked, False otherwise
        """
        session = (
            db.query(UserSession).filter(UserSession.token_jti == token_jti).first()
        )

        if session:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()

            # Add to Redis blacklist for fast lookup
            try:
                blacklist = TokenBlacklist()
                blacklist.add_token(token_jti, ttl_seconds)
            except Exception as e:
                logger.warning(f"Failed to add token to Redis blacklist: {str(e)}")

            logger.info(f"Revoked token JTI: {token_jti}")
            return True

        logger.warning(f"Token JTI not found: {token_jti}")
        return False

    @staticmethod
    def revoke_all_user_sessions(user_id: int, db: Session) -> int:
        """
        Revoke all active sessions for a user (logout from all devices)

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Number of sessions revoked
        """
        sessions = (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.is_active)
            .all()
        )

        count = 0
        for session in sessions:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)

            # Add tokens to Redis blacklist
            try:
                blacklist = TokenBlacklist()
                # Calculate remaining TTL
                remaining_seconds = int(
                    (session.expires_at - datetime.now(timezone.utc)).total_seconds()
                )
                if remaining_seconds > 0:
                    blacklist.add_token(session.token_jti, remaining_seconds)
                    if session.refresh_token_jti:
                        blacklist.add_token(
                            session.refresh_token_jti, remaining_seconds
                        )
            except Exception as e:
                logger.warning(f"Failed to add tokens to Redis blacklist: {str(e)}")

            count += 1

        db.commit()

        # Also delete Redis sessions
        try:
            session_store = SessionStore()
            session_store.delete_user_sessions(user_id)
        except Exception as e:
            logger.warning(f"Failed to delete Redis sessions: {str(e)}")

        logger.info(f"Revoked {count} sessions for user {user_id}")

        return count

    @staticmethod
    def is_token_revoked(token_jti: str, db: Session) -> bool:
        """
        Check if a token has been revoked

        Args:
            token_jti: JWT ID to check
            db: Database session

        Returns:
            True if token is revoked, False otherwise
        """
        # Fast check: Redis blacklist (cache layer)
        try:
            blacklist = TokenBlacklist()
            if blacklist.is_token_blacklisted(token_jti):
                return True
        except Exception as e:
            logger.warning(f"Redis blacklist check failed: {str(e)}")

        # Fallback: Database check
        session = (
            db.query(UserSession).filter(UserSession.token_jti == token_jti).first()
        )

        # If session not found, allow token (stateless JWT validation)
        # This allows tokens that were created before session tracking was implemented
        if not session:
            return False  # Token not found = allow (stateless mode)

        return not session.is_active
