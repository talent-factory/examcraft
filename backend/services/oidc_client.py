"""OIDC client against tessera/Zitadel (EXAMCRAFT-125, ADR 0008).

Authorization-code flow with PKCE for a confidential client, ID-token
verification against the JWKS, userinfo merge. Plain ``httpx`` calls so
discovery, token and JWKS endpoints can all be mocked with respx.

Configuration is read from the environment on every call (no import-time
snapshot), so tests and key rotation of secrets need no reload.
"""

import logging
import os
import time
from functools import lru_cache
from typing import Optional
from urllib.parse import urlencode

import httpx
from jose import jwt as jose_jwt
from jose.exceptions import JWTError

logger = logging.getLogger(__name__)

HTTP_TIMEOUT_SECONDS = 5


class OidcNotConfiguredError(RuntimeError):
    """A required OIDC_* environment variable is missing."""


class UnknownSigningKeyError(Exception):
    """The ``kid`` of the ID token is in no key of the JWKS endpoint."""


def _env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise OidcNotConfiguredError(f"{name} ist nicht gesetzt")
    return value


def issuer() -> str:
    return _env("OIDC_ISSUER").rstrip("/")


def client_id() -> str:
    return _env("OIDC_CLIENT_ID")


def redirect_uri() -> str:
    return _env("OIDC_REDIRECT_URI")


# Environments in which defaults for local development are acceptable.
DEV_ENVIRONMENTS = frozenset({"development", "dev", "test", "e2e", "local"})


def is_dev_environment() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() in DEV_ENVIRONMENTS


def frontend_base_url() -> str:
    """Base URL for redirects. Outside development it must be configured:
    a silent ``localhost`` default would send every user to localhost."""
    value = os.getenv("FRONTEND_URL")
    if not value:
        if not is_dev_environment():
            raise OidcNotConfiguredError("FRONTEND_URL ist nicht gesetzt")
        value = "http://localhost:3000"
    return value.rstrip("/")


def scopes() -> list[str]:
    """OIDC scopes plus Zitadel's org scope for the ``examcraft`` org.

    Zitadel picks login page and policy (incl. the Google/Microsoft/GitHub
    buttons) by the org requested at login, not by the org of the app. The
    scope also makes Zitadel enforce that the user belongs to that org.
    """
    result = os.getenv("OIDC_SCOPES", "openid email profile").split()
    org_id = os.getenv("ZITADEL_ORG_ID")
    if org_id:
        result.append(f"urn:zitadel:iam:org:id:{org_id}")
    return result


# Discovery and JWKS are cached per time bucket, so a changed endpoint or a
# withdrawn signing key is picked up without a restart.
_CACHE_TTL_SECONDS = 600


def _bucket() -> int:
    return int(time.time() // _CACHE_TTL_SECONDS)


def _discovery(issuer_url: str) -> dict:
    return _discovery_cached(issuer_url, _bucket())


def _jwks(jwks_uri: str) -> dict:
    return _jwks_cached(jwks_uri, _bucket())


@lru_cache(maxsize=4)
def _discovery_cached(issuer_url: str, _bucket_id: int) -> dict:
    resp = httpx.get(
        f"{issuer_url}/.well-known/openid-configuration", timeout=HTTP_TIMEOUT_SECONDS
    )
    resp.raise_for_status()
    try:
        disco = resp.json()
    except ValueError as exc:
        raise httpx.DecodingError("Discovery lieferte kein JSON") from exc
    if not isinstance(disco, dict):
        raise httpx.DecodingError("Discovery ist kein JSON-Objekt")
    return disco


@lru_cache(maxsize=4)
def _jwks_cached(jwks_uri: str, _bucket_id: int) -> dict:
    resp = httpx.get(jwks_uri, timeout=HTTP_TIMEOUT_SECONDS)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError as exc:
        raise httpx.DecodingError("JWKS lieferte kein JSON") from exc
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("keys"), list)
        or not all(isinstance(key, dict) for key in data["keys"])
    ):
        raise httpx.DecodingError("JWKS ohne gültige keys-Liste")
    return data


def clear_caches() -> None:
    _discovery_cached.cache_clear()
    _jwks_cached.cache_clear()


def build_authorize_url(
    state: str, code_challenge: str, nonce: str, force_login: bool = False
) -> str:
    """Authorize URL. ``force_login`` sets ``prompt=login`` (re-authentication)."""
    disco = _discovery(issuer())
    query = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(scopes()),
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if force_login:
        # prompt=login makes Zitadel ask for credentials even with an SSO
        # session; max_age=0 makes it put a fresh auth_time into the ID token.
        query["prompt"] = "login"
        query["max_age"] = "0"
    return f"{disco['authorization_endpoint']}?{urlencode(query)}"


def exchange_code(code: str, code_verifier: str) -> dict:
    disco = _discovery(issuer())
    resp = httpx.post(
        disco["token_endpoint"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(),
            "code_verifier": code_verifier,
        },
        auth=(client_id(), _env("OIDC_CLIENT_SECRET")),
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    if resp.status_code >= 400:
        # Keep the IdP's reason (invalid_grant vs invalid_client vs redirect
        # mismatch) in the log; never the code, secret or tokens.
        try:
            body = resp.json()
            reason = f"{body.get('error')}: {body.get('error_description')}"
        except (ValueError, AttributeError):
            reason = "keine auswertbare Antwort"
        logger.error(
            "Token-Exchange vom IdP abgelehnt (HTTP %s, %s).", resp.status_code, reason
        )
        resp.raise_for_status()
    try:
        tokens = resp.json()
    except ValueError as exc:
        raise httpx.DecodingError("Token-Endpoint lieferte kein JSON") from exc
    if not isinstance(tokens, dict) or not tokens.get("id_token"):
        raise httpx.DecodingError("Token-Response ohne id_token")
    return tokens


def _find_jwk(jwks: dict, kid: Optional[str]) -> Optional[dict]:
    return next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)


def validate_id_token(id_token: str, nonce: str) -> dict:
    """Verify signature (RS256), ``aud``, ``iss``, expiry and (if given) nonce.

    Raises ``jose.exceptions.JWTError`` for an invalid token and
    ``UnknownSigningKeyError`` if the ``kid`` is unknown even after one
    refetch of the JWKS (Zitadel rotates signing keys automatically).
    """
    disco = _discovery(issuer())
    jwks_uri = disco["jwks_uri"]
    kid = jose_jwt.get_unverified_header(id_token).get("kid")
    jwk = _find_jwk(_jwks(jwks_uri), kid)
    if jwk is None:
        _jwks_cached.cache_clear()
        jwk = _find_jwk(_jwks(jwks_uri), kid)
    if jwk is None:
        raise UnknownSigningKeyError(f"Kein JWKS-Key für kid={kid!r}")
    claims = jose_jwt.decode(
        id_token,
        jwk,
        algorithms=["RS256"],
        audience=client_id(),
        issuer=issuer(),
        options={"verify_at_hash": False},
    )
    # The nonce is mandatory: it binds the token to this browser's login start.
    if not nonce or claims.get("nonce") != nonce:
        raise JWTError("nonce stimmt nicht überein")
    return claims


# Identity and validity come from the verified ID token only; the userinfo
# response must never overwrite these claims.
_ID_TOKEN_ONLY_CLAIMS = frozenset(
    {"sub", "iss", "aud", "exp", "iat", "nbf", "auth_time", "nonce", "azp"}
)


def merge_userinfo_claims(id_claims: dict, access_token: Optional[str]) -> dict:
    """Add profile claims from the userinfo endpoint to the ID-token claims.

    Zitadel only puts email/profile claims into the ID token with
    ``id_token_userinfo_assertion``; userinfo always has them. If userinfo is
    unreachable or belongs to another ``sub`` (OIDC Core 5.3.2), only the ID
    token counts.
    """
    if not access_token:
        return id_claims
    try:
        disco = _discovery(issuer())
        resp = httpx.get(
            disco.get("userinfo_endpoint") or f"{issuer()}/oidc/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        userinfo = resp.json()
    except (httpx.HTTPError, ValueError):
        logger.warning(
            "Userinfo-Abruf fehlgeschlagen, nutze ID-Token-Claims.", exc_info=True
        )
        return id_claims
    if not isinstance(userinfo, dict) or userinfo.get("sub") != id_claims.get("sub"):
        logger.error(
            "Userinfo gehört zu einem anderen sub (token sub=%s), nutze ID-Token-Claims.",
            id_claims.get("sub"),
        )
        return id_claims
    profile = {k: v for k, v in userinfo.items() if k not in _ID_TOKEN_ONLY_CLAIMS}
    return {**id_claims, **profile}
