"""OIDC login against tessera/Zitadel (EXAMCRAFT-125, ADR 0008).

Mounted under ``/api/v1/auth``: the callback path ``/api/v1/auth/callback`` is
the contract with the Zitadel client (tessera Terraform
``examcraft_web_redirect_uris``). Changing it needs a Terraform change.

BFF pattern: the backend runs the authorization-code flow with PKCE as a
confidential client and keeps the login as a server-side session. The
browser only holds an opaque httpOnly cookie, never a token.

Guard rails:

* ``state`` (CSRF) and the PKCE verifier travel in short-lived httpOnly
  cookies set by ``/login``; a mismatch is a 400.
* The callback always ends in a redirect to the frontend (``/login?error=…``
  on failure), never in a raw 4xx/5xx page, because it is a top-level
  browser navigation.
* ``record_login`` runs once per new session, in the callback.
* The user's ``status`` is checked here and on every request
  (``utils.auth_utils.get_current_user``); there is no sync with Zitadel.
"""

import logging
import secrets
from datetime import datetime, timezone
from base64 import urlsafe_b64encode
from hashlib import sha256
from hmac import compare_digest
from typing import Optional

import httpx
from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from jose.exceptions import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User, UserStatus
from services import oidc_client, session_service
from errors import api_error
from services.audit_service import AuditService
from services.translation_service import get_request_locale
from services.auth_service import AuthService
from services.user_provisioning import (
    AccountNotMigratedError,
    EmailConflictError,
    MissingClaimError,
    ProvisioningError,
    UserLimitReachedError,
    get_or_provision_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Long enough for the redirect round trip to Zitadel incl. a social login.
_FLOW_COOKIE_MAX_AGE_SECONDS = 600
_FLOW_COOKIES = ("oidc_state", "oidc_verifier", "oidc_nonce", "oidc_reauth")
# A forced re-authentication must show an auth_time at most this old.
_REAUTH_AUTH_TIME_TOLERANCE_SECONDS = 120


def cookie_secure() -> bool:
    """``Secure`` unless ``ENVIRONMENT`` names a dev environment (browsers drop
    it on http://localhost). An unknown name (``prod``, ``staging``) gets
    ``Secure``. An *unset* ``ENVIRONMENT`` counts as development, like
    everywhere else in this code base, so production must set it (it does in
    ``fly.toml``)."""
    return not oidc_client.is_dev_environment()


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = (
        urlsafe_b64encode(sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    return verifier, challenge


def _frontend_base() -> str:
    """Frontend base URL for redirects; never raises.

    A redirect helper that throws turns every error path into a raw 500.
    Without ``FRONTEND_URL`` outside dev the redirect becomes relative: the
    frontend proxies ``/api/`` on its own domain, so ``/login`` resolves
    against the same origin the user came from.
    """
    try:
        return oidc_client.frontend_base_url()
    except oidc_client.OidcNotConfiguredError:
        logger.critical("FRONTEND_URL fehlt, Redirects werden relativ ausgeliefert.")
        return ""


def _error_redirect(error_code: str) -> Response:
    response = RedirectResponse(
        f"{_frontend_base()}/login?error={error_code}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    for name in _FLOW_COOKIES:
        response.delete_cookie(name)
    return response


def _auth_time(claims: dict) -> Optional[datetime]:
    value = claims.get("auth_time")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def set_session_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        session_service.SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        max_age=max_age_seconds,
        path="/",
    )


@router.get("/login")
def login(reauth: bool = False) -> Response:
    """Start the authorization-code flow (PKCE) against tessera/Zitadel.

    ``reauth=true`` forces a fresh authentication (``prompt=login``), used
    before sensitive actions such as starting an impersonation.
    """
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    verifier, challenge = _pkce_pair()
    try:
        url = oidc_client.build_authorize_url(
            state=state, code_challenge=challenge, nonce=nonce, force_login=reauth
        )
    except (httpx.HTTPError, oidc_client.OidcNotConfiguredError, KeyError):
        logger.exception("OIDC-Discovery für /login fehlgeschlagen.")
        return _error_redirect("idp_unavailable")
    response = RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    if not reauth:
        # A leftover marker of an abandoned reauth must not harden a normal login.
        response.delete_cookie("oidc_reauth", path="/")
    for name, value in (
        ("oidc_state", state),
        ("oidc_verifier", verifier),
        ("oidc_nonce", nonce),
        *((("oidc_reauth", "1"),) if reauth else ()),
    ):
        response.set_cookie(
            name,
            value,
            httponly=True,
            secure=cookie_secure(),
            samesite="lax",
            max_age=_FLOW_COOKIE_MAX_AGE_SECONDS,
            path="/",
        )
    return response


@router.get("/callback")
def callback(
    request: Request,
    state: Optional[str] = None,
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Response:
    cookie_state = request.cookies.get("oidc_state")
    verifier = request.cookies.get("oidc_verifier")
    nonce = request.cookies.get("oidc_nonce")
    # .encode(): compare_digest rejects non-ASCII str with a TypeError.
    if (
        state is None
        or cookie_state is None
        or verifier is None
        or nonce is None
        or not compare_digest(cookie_state.encode(), state.encode())
    ):
        # The callback is a top-level navigation: a stale or overwritten flow
        # (slow social login, two tabs, back button) must end on the login
        # page, not on an API error page. No code is exchanged, so the CSRF
        # protection is the same.
        logger.info("OIDC-Callback mit ungültigem oder fehlendem state.")
        return _error_redirect("login_expired")

    if error is not None or code is None:
        logger.info("OIDC-Callback ohne Code (error=%.100r).", error)
        return _error_redirect("login_cancelled")

    ip = request.client.host if request.client else None
    reauth = request.cookies.get("oidc_reauth") == "1"
    try:
        tokens = oidc_client.exchange_code(code=code, code_verifier=verifier)
        claims = oidc_client.validate_id_token(tokens["id_token"], nonce=nonce)
        claims = oidc_client.merge_userinfo_claims(claims, tokens.get("access_token"))
    except oidc_client.OidcNotConfiguredError:
        # A missing OIDC_* variable is an operator problem, not a user one.
        logger.critical("OIDC-Callback: OIDC-Konfiguration unvollständig.")
        return _error_redirect("idp_unavailable")
    except httpx.HTTPError:
        logger.exception("OIDC-Callback: IdP nicht erreichbar oder lehnt ab.")
        return _error_redirect("login_failed")
    except (
        oidc_client.UnknownSigningKeyError,
        JWTError,
        KeyError,
        ValueError,
        AttributeError,
        TypeError,
        httpx.InvalidURL,
    ):
        # An unusable token response or a bad ID token (signature, aud, iss,
        # nonce, unknown kid) or a malformed discovery/JWKS document.
        logger.exception("OIDC-Callback: Token-Validierung fehlgeschlagen.")
        return _error_redirect("login_failed")

    authenticated_at = _auth_time(claims)
    if reauth:
        # The step-up only counts if Zitadel really asked for credentials just now.
        age = (
            (datetime.now(timezone.utc) - authenticated_at).total_seconds()
            if authenticated_at is not None
            else None
        )
        if age is None or age > _REAUTH_AUTH_TIME_TOLERANCE_SECONDS or age < -60:
            logger.warning("Reauth ohne frischen auth_time (age=%s).", age)
            return _error_redirect("reauth_failed")

    try:
        user, _created = get_or_provision_user(db, claims)
    except AccountNotMigratedError:
        logger.warning(
            "OIDC-Login: Konto ist noch nicht migriert, kein zitadel_sub (sub=%s).",
            claims.get("sub"),
        )
        return _error_redirect("account_not_migrated")
    except EmailConflictError:
        logger.warning(
            "OIDC-Login: E-Mail gehört zu einem anderen Benutzer (sub=%s).",
            claims.get("sub"),
        )
        return _error_redirect("email_conflict")
    except UserLimitReachedError as exc:
        logger.warning("OIDC-Login: Benutzerlimit der Institution %s erreicht.", exc)
        return _error_redirect("user_limit")
    except MissingClaimError as exc:
        logger.error(
            "OIDC-Login: Claim %s fehlt (Scope oder Userinfo prüfen), sub=%s.",
            exc,
            claims.get("sub"),
        )
        return _error_redirect("claims_missing")
    except (SQLAlchemyError, ProvisioningError):
        db.rollback()
        logger.exception("OIDC-Callback: Benutzer konnte nicht angelegt werden.")
        return _error_redirect("login_failed")

    if user.status != UserStatus.ACTIVE.value:
        logger.warning(
            "OIDC-Login abgewiesen: user_id=%s status=%s", user.id, user.status
        )
        AuditService.log_login(
            db,
            user.id,
            success=False,
            request=request,
            error_message=f"Login abgewiesen: Status {user.status}",
            login_method="zitadel",
        )
        return _error_redirect("account_inactive")

    # The redirect target is resolved before the session exists, so a
    # configuration problem can never leave a session without a cookie.
    target = f"{_frontend_base()}/"

    # record_login once per new session, then create the session (one commit).
    try:
        AuthService.record_login(user, ip)
        token, _row = session_service.create_session(
            db, user.id, authenticated_at=authenticated_at
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception(
            "OIDC-Callback: Session für user_id=%s nicht angelegt.", user.id
        )
        return _error_redirect("login_failed")
    try:
        # Retention: expired sessions are deleted opportunistically at login,
        # so no rows outlive their 14 days (30 minutes for impersonation).
        session_service.purge_expired(db)
    except Exception:
        db.rollback()
        logger.exception("Bereinigung abgelaufener Sessions fehlgeschlagen.")
    try:
        AuditService.log_login(
            db, user.id, success=True, request=request, login_method="zitadel"
        )
    except Exception:
        logger.exception("Audit-Eintrag für Login von User %s fehlgeschlagen.", user.id)

    response = RedirectResponse(target, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    set_session_cookie(
        response, token, int(session_service.SESSION_MAX_AGE.total_seconds())
    )
    for name in _FLOW_COOKIES:
        response.delete_cookie(name)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session_token: Optional[str] = Cookie(
        default=None, alias=session_service.SESSION_COOKIE_NAME
    ),
    impersonation_token: Optional[str] = Cookie(
        default=None, alias=session_service.IMPERSONATION_COOKIE_NAME
    ),
    db: Session = Depends(get_db),
) -> None:
    """End the local session only (Zitadel's SSO session stays).

    Idempotent: no or an unknown session is a no-op. While impersonating,
    logging out ends the impersonation and keeps the admin logged in
    (TF-741), instead of ending the admin's own session by accident.
    """
    try:
        effective = session_service.resolve_effective_session(
            db, session_token, impersonation_token
        )
    except Exception:
        db.rollback()
        logger.exception("Logout: Session konnte nicht aufgelöst werden.")
        effective = None

    if effective is not None and effective.impersonation_session_id is not None:
        # Ends the impersonation only; the admin stays logged in (TF-741).
        response.delete_cookie(session_service.IMPERSONATION_COOKIE_NAME, path="/")
        try:
            AuthService.end_impersonation_session(
                impersonation_session_id=effective.impersonation_session_id,
                db=db,
                request=request,
            )
        except Exception:
            db.rollback()
            logger.exception(
                "Logout: Impersonation %s nicht beendet (admin_id=%s).",
                effective.impersonation_session_id,
                effective.impersonator_id,
            )
            _delete_session_safely(db, impersonation_token)
        return None

    # Logout is best effort: cookies go first (local, cannot fail), then the
    # rows, each step on its own so one failure never keeps the others alive.
    response.delete_cookie(session_service.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(session_service.IMPERSONATION_COOKIE_NAME, path="/")
    if effective is not None:
        try:
            # A normal logout must not leave an open impersonation behind.
            AuthService.end_own_impersonation_session(
                admin_user_id=effective.user_id, db=db, request=request
            )
            AuditService.log_logout(db, effective.user_id, request=request)
        except Exception:
            db.rollback()
            logger.exception(
                "Logout: Impersonation-Ende oder Audit fehlgeschlagen (user_id=%s).",
                effective.user_id,
            )
    _delete_session_safely(db, session_token)
    _delete_session_safely(db, impersonation_token)
    return None


def _delete_session_safely(db: Session, token: Optional[str]) -> None:
    try:
        session_service.delete_session(db, token)
    except Exception:
        db.rollback()
        logger.exception("Logout: Session-Zeile konnte nicht gelöscht werden.")


# ---------------------------------------------------------------------------
# Test login (E2E only)
# ---------------------------------------------------------------------------


def _test_login_requested() -> bool:
    import os

    return os.getenv("E2E_TEST_LOGIN", "").lower() in ("1", "true", "yes")


class TestLoginRequest(BaseModel):
    __test__ = False  # not a pytest class

    email: EmailStr


def assert_test_login_safe() -> None:
    """Refuse to start if the test login is switched on outside a dev environment.

    Positive list on purpose: ``ENVIRONMENT=prod``, ``staging`` or an unset
    variable in production must not slip through a check for the literal
    string ``production``."""
    if _test_login_requested() and not oidc_client.is_dev_environment():
        raise RuntimeError(
            "FATAL: E2E_TEST_LOGIN darf nur in einer Dev-Umgebung gesetzt sein "
            "(ENVIRONMENT=development/dev/test/e2e/local). Start verweigert."
        )


# Module import happens at app startup: the check below is the hard refusal,
# and the route only exists when the flag is set outside production.
assert_test_login_safe()

if _test_login_requested():

    @router.post("/test-login", status_code=status.HTTP_204_NO_CONTENT)
    def test_login(
        payload: TestLoginRequest,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
    ) -> None:
        """Log in an existing, active user by e-mail without Zitadel (E2E only)."""
        user = (
            db.query(User)
            .filter(func.lower(User.email) == payload.email.lower())
            .first()
        )
        if user is None or user.status != UserStatus.ACTIVE.value:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                "auth_user_not_found",
                get_request_locale(request),
            )
        token, _row = session_service.create_session(
            db, user.id, authenticated_at=datetime.now(timezone.utc)
        )
        set_session_cookie(
            response, token, int(session_service.SESSION_MAX_AGE.total_seconds())
        )
        return None
