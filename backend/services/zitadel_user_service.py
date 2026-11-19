"""Zitadel-Benutzerverwaltung für die DSGVO-Löschung und den Export (EXAMCRAFT-128).

ADR 0008: Anmeldung und Identität liegen in tessera/Zitadel. Eine DSGVO-
Löschung muss deshalb auch den Zitadel-User entfernen, sonst bleibt das
Profil (E-Mail, Name, IdP-Links) im Identity Provider zurück.

Authentisierung: Service-User ``examcraft-user-delete`` per OAuth2
Client-Credentials. Konfiguration über Umgebungsvariablen (Fly-Secrets auf
``examcraft-api`` und ``examcraft-celery``):

  - ``ZITADEL_ISSUER``: Basis-URL der Instanz, z. B. ``https://login.example.ch``
  - ``ZITADEL_USER_DELETE_CLIENT_ID`` / ``ZITADEL_USER_DELETE_CLIENT_SECRET``

Fehlerklassen:
  - ``ZitadelTransientError`` (Unterklasse von ``ConnectionError``): Netzwerk-
    fehler, Timeout, 5xx/429. Der Celery-Task retried diese automatisch.
  - ``ZitadelError``: Konfiguration fehlt,
    Auth abgelehnt, andere 4xx. Nicht retry-fähig, sichtbar als Fehlschlag.
"""

import logging
import os
import time
from typing import Any, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10.0
_TOKEN_SCOPE = "openid urn:zitadel:iam:org:project:id:zitadel:aud"


class ZitadelError(Exception):
    """Dauerhafter Fehler (Konfiguration, Autorisierung, 4xx).

    Bewusst KEINE ``RuntimeError``-Unterklasse: ``api/gdpr.py`` behandelt
    ``RuntimeError`` als fail-closed-Abbruch des Audit-Logs, ein Zitadel-Problem
    soll dort nicht als DB-/Audit-Fehler erscheinen.
    """


class ZitadelConfigError(ZitadelError):
    """Zitadel-Konfiguration (Umgebungsvariablen) fehlt oder ist unvollständig."""


class ZitadelAuthError(ZitadelError):
    """Zitadel lehnt die Credentials ab (HTTP 401/403)."""


class ZitadelTransientError(ConnectionError):
    """Vorübergehender Fehler (Netzwerk, Timeout, 5xx, 429): Retry sinnvoll."""


def _config() -> tuple[str, str, str]:
    issuer = os.getenv("ZITADEL_ISSUER", "").strip().rstrip("/")
    client_id = os.getenv("ZITADEL_USER_DELETE_CLIENT_ID", "").strip()
    client_secret = os.getenv("ZITADEL_USER_DELETE_CLIENT_SECRET", "").strip()
    if not (issuer and client_id and client_secret):
        raise ZitadelConfigError(
            "Zitadel nicht konfiguriert (ZITADEL_ISSUER, "
            "ZITADEL_USER_DELETE_CLIENT_ID, ZITADEL_USER_DELETE_CLIENT_SECRET)"
        )
    return issuer, client_id, client_secret


def _raise_for_status(response: httpx.Response, what: str) -> None:
    status = response.status_code
    if status >= 500 or status == 429:
        raise ZitadelTransientError(f"Zitadel {what}: HTTP {status}")
    if status in (401, 403):
        raise ZitadelAuthError(f"Zitadel {what}: HTTP {status}")
    if status >= 400:
        raise ZitadelError(f"Zitadel {what}: HTTP {status}")


def _json(response: httpx.Response, what: str) -> dict[str, Any]:
    """Parst die Antwort; ein Nicht-JSON-Body (Proxy, Wartungsseite) ist transient."""
    try:
        body = response.json()
    except ValueError as exc:
        raise ZitadelTransientError(f"Zitadel {what}: ungültige Antwort") from exc
    if not isinstance(body, dict):
        raise ZitadelTransientError(f"Zitadel {what}: unerwartetes Antwortformat")
    return body


def _access_token(
    client: httpx.Client, issuer: str, client_id: str, secret: str
) -> str:
    response = client.post(
        f"{issuer}/oauth/v2/token",
        data={"grant_type": "client_credentials", "scope": _TOKEN_SCOPE},
        auth=(client_id, secret),
    )
    _raise_for_status(response, "Token-Abruf")
    token = _json(response, "Token-Abruf").get("access_token")
    if not token:
        raise ZitadelError("Zitadel Token-Abruf: keine access_token-Antwort")
    return token


def _request(method: str, sub: str) -> Optional[httpx.Response]:
    """Führt einen User-API-Aufruf aus. ``None`` bei 404 (User existiert nicht)."""
    issuer, client_id, secret = _config()
    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            token = _access_token(client, issuer, client_id, secret)
            response = client.request(
                method,
                f"{issuer}/v2/users/{quote(sub, safe='')}",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise ZitadelTransientError(f"Zitadel nicht erreichbar: {exc}") from exc

    if response.status_code == 404:
        # Nur ein echtes Zitadel-NOT_FOUND (gRPC-Code 5) heisst "User existiert
        # nicht". Ein 404 von falschem Issuer, Proxy oder Pfad darf nicht als
        # erledigt gelten, sonst bliebe der IdP-User unbemerkt zurück.
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict) and body.get("code") in (5, "NOT_FOUND"):
            return None
        raise ZitadelError(f"Zitadel {method} User: HTTP 404 ohne NOT_FOUND-Antwort")
    _raise_for_status(response, f"{method} User")
    return response


def delete_zitadel_user(sub: str) -> bool:
    """Löscht den Zitadel-User idempotent.

    Returns:
        ``True`` wenn der User gelöscht wurde, ``False`` wenn er bereits nicht
        mehr existierte (404, z. B. nach einem früheren Teilerfolg).

    Raises:
        ZitadelError / ZitadelTransientError: siehe Modul-Docstring.
    """
    deleted = _request("DELETE", sub) is not None
    if deleted:
        logger.info("Zitadel-User gelöscht (sub=%s)", sub)
    else:
        # 404 gilt als bereits gelöscht (Idempotenz). Ein falsches ``sub``
        # sähe identisch aus, deshalb sichtbar loggen.
        logger.warning("Zitadel-User nicht gefunden (sub=%s), gilt als gelöscht", sub)
    return deleted


def fetch_zitadel_profile(sub: str) -> Optional[dict[str, Any]]:
    """Liest die Zitadel-Profildaten des Users für den DSGVO-Export.

    Returns:
        Das ``user``-Objekt der Zitadel-API, ``None`` wenn der User dort nicht
        (mehr) existiert.
    """
    response = _request("GET", sub)
    if response is None:
        return None
    body = _json(response, "GET User")
    if "user" not in body:
        raise ZitadelError("Zitadel GET User: Antwort ohne 'user'")
    return body["user"]


# ---------------------------------------------------------------------------
# Konfigurations-Health-Check (EXAMCRAFT-134)
# ---------------------------------------------------------------------------

_HEALTH_CACHE_TTL_SECONDS = 300.0
_health_cache: Optional[tuple[float, str]] = None


def check_zitadel_user_delete_config(*, use_cache: bool = False) -> str:
    """Prüft Konfiguration und Credentials des Löschungs-Service-Users.

    Holt nur ein Token (Client-Credentials), ruft aber nie die User-API auf und
    löscht nichts. So fällt eine fehlende oder falsche Secret auf, bevor eine
    fällige DSGVO-Löschung daran scheitert. Wirft nie eine Exception.

    Args:
        use_cache: Ergebnis 5 Minuten zwischenspeichern (für den
            ``/api/v1/health``-Endpoint, der häufig gepollt wird). Auch
            Fehlerstatus werden zwischengespeichert.

    Returns:
        ``ok``: Token-Abruf erfolgreich.
        ``not_configured``: Mindestens eine der drei Variablen fehlt.
        ``auth_rejected``: Zitadel lehnt die Credentials ab (HTTP 401/403).
        ``unreachable``: Netzwerkfehler, Timeout, 5xx/429 (transient).
        ``error``: Anderer Fehler (z. B. falscher Issuer-Pfad mit 404, ungültige
            Issuer-URL, Antwort ohne ``access_token``).
    """
    global _health_cache
    now = time.monotonic()
    if (
        use_cache
        and _health_cache
        and now - _health_cache[0] < _HEALTH_CACHE_TTL_SECONDS
    ):
        return _health_cache[1]

    detail: Optional[BaseException] = None
    try:
        issuer, client_id, secret = _config()
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            _access_token(client, issuer, client_id, secret)
        status = "ok"
    except ZitadelConfigError as exc:
        status, detail = "not_configured", exc
    except ZitadelAuthError as exc:
        status, detail = "auth_rejected", exc
    except (httpx.UnsupportedProtocol, httpx.InvalidURL) as exc:
        # Ungültiger Issuer (kein Schema, Leerzeichen): dauerhafter Konfigurationsfehler.
        status, detail = "error", exc
    except (ZitadelTransientError, httpx.TransportError) as exc:
        status, detail = "unreachable", exc
    except Exception as exc:  # noqa: BLE001 - Health-Check darf nie werfen
        status, detail = "error", exc

    if detail is not None:
        # Ausserhalb von Production ist eine fehlende Konfiguration normal.
        level = (
            logging.ERROR
            if os.getenv("ENVIRONMENT") == "production"
            else logging.WARNING
        )
        logger.log(
            level,
            "Zitadel-Löschkonfiguration (examcraft-user-delete): %s (%s: %s)",
            status,
            type(detail).__name__,
            detail,
        )
    if use_cache:
        _health_cache = (now, status)
    return status
