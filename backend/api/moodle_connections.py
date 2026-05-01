"""Moodle-Connections API (TF-336 Subarea C).

Endpoints (alle unter ``moodle:configure``):

* ``GET    /api/v1/admin/moodle-connections``      — Liste (max. 1 pro Inst.)
* ``POST   /api/v1/admin/moodle-connections``      — anlegen
* ``GET    /api/v1/admin/moodle-connections/{id}`` — Detail (Token maskiert)
* ``PATCH  /api/v1/admin/moodle-connections/{id}`` — base_url/token ändern
* ``DELETE /api/v1/admin/moodle-connections/{id}`` — entfernen
* ``POST   /api/v1/admin/moodle-connections/{id}/test`` — Token validieren

Multi-Tenancy: jede Connection ist 1:1 an die Institution gekoppelt
(``moodle_connections.institution_id`` UNIQUE). Lesen/Schreiben filtert
auf ``current_user.institution_id``.

Token-Verschlüsselung: Plaintext-Token wird via Fernet
(``utils.secret_encryption``) verschlüsselt persistiert. Der Token wird
**nie** roh ausgespielt; das Detail-Schema liefert ``token_masked`` als
``****<letzte 4 Zeichen>``.
"""

import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models.auth import User
from models.submission import MoodleConnection
from utils.auth_utils import require_permission
from utils.secret_encryption import (
    SecretEncryptionError,
    decrypt_secret,
    encrypt_secret,
)


logger = logging.getLogger(__name__)


_STRICT_OUT = ConfigDict(extra="forbid")


router = APIRouter(
    prefix="/api/v1/admin/moodle-connections",
    tags=["MoodleConnections"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class MoodleConnectionOut(BaseModel):
    model_config = _STRICT_OUT

    id: int
    institution_id: int
    base_url: str
    token_masked: str
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MoodleConnectionListOut(BaseModel):
    model_config = _STRICT_OUT

    items: list[MoodleConnectionOut]
    total: int


class MoodleConnectionCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    base_url: HttpUrl
    token: str = Field(min_length=8, max_length=255)


class MoodleConnectionUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    base_url: HttpUrl | None = None
    token: str | None = Field(default=None, min_length=8, max_length=255)


class MoodleConnectionTestOut(BaseModel):
    model_config = _STRICT_OUT

    ok: bool
    site_name: str | None = None
    site_url: str | None = None
    user_full_name: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_token(token_plaintext: str) -> str:
    """``****<last 4>``. The mask is intentionally short: full-length
    masks would leak the token length, which is itself a fingerprint
    on small Moodle deploys.
    """
    if len(token_plaintext) <= 4:
        return "****"
    return f"****{token_plaintext[-4:]}"


def _to_out(
    connection: MoodleConnection, *, token_plaintext: str
) -> MoodleConnectionOut:
    return MoodleConnectionOut(
        id=connection.id,
        institution_id=connection.institution_id,
        base_url=connection.base_url,
        token_masked=_mask_token(token_plaintext),
        last_used_at=connection.last_used_at,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


def _decrypt_or_500(connection: MoodleConnection) -> str:
    try:
        return decrypt_secret(connection.token_encrypted)
    except SecretEncryptionError as exc:
        logger.error(
            "Konnte Moodle-Token für connection_id=%s nicht entschlüsseln: %s",
            connection.id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Token-Verschlüsselung defekt. Operations-Team "
                "kontaktieren — vermutlich Schlüssel-Rotation ohne "
                "Re-Encryption."
            ),
        ) from exc


def _load_for_user(*, db: Session, user: User, connection_id: int) -> MoodleConnection:
    connection = (
        db.query(MoodleConnection)
        .filter(
            MoodleConnection.id == connection_id,
            MoodleConnection.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="Moodle-Verbindung nicht gefunden")
    return connection


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=MoodleConnectionListOut)
async def list_connections(
    current_user: User = Depends(require_permission("moodle:configure")),
    db: Session = Depends(get_db),
) -> MoodleConnectionListOut:
    """Liefert die (höchstens eine) Connection der Institution."""
    rows = (
        db.query(MoodleConnection)
        .filter(MoodleConnection.institution_id == current_user.institution_id)
        .order_by(MoodleConnection.id)
        .all()
    )
    items = [_to_out(c, token_plaintext=_decrypt_or_500(c)) for c in rows]
    return MoodleConnectionListOut(items=items, total=len(items))


@router.post(
    "",
    response_model=MoodleConnectionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    body: MoodleConnectionCreateIn,
    current_user: User = Depends(require_permission("moodle:configure")),
    db: Session = Depends(get_db),
) -> MoodleConnectionOut:
    """Connection anlegen. 409, falls bereits eine existiert."""
    encrypted = encrypt_secret(body.token)
    connection = MoodleConnection(
        institution_id=current_user.institution_id,
        base_url=str(body.base_url).rstrip("/"),
        token_encrypted=encrypted,
    )
    db.add(connection)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Es existiert bereits eine Moodle-Verbindung für diese Institution.",
        ) from exc
    db.refresh(connection)
    return _to_out(connection, token_plaintext=body.token)


@router.get("/{connection_id}", response_model=MoodleConnectionOut)
async def get_connection(
    connection_id: int,
    current_user: User = Depends(require_permission("moodle:configure")),
    db: Session = Depends(get_db),
) -> MoodleConnectionOut:
    connection = _load_for_user(db=db, user=current_user, connection_id=connection_id)
    token = _decrypt_or_500(connection)
    return _to_out(connection, token_plaintext=token)


@router.patch("/{connection_id}", response_model=MoodleConnectionOut)
async def update_connection(
    connection_id: int,
    body: MoodleConnectionUpdateIn,
    current_user: User = Depends(require_permission("moodle:configure")),
    db: Session = Depends(get_db),
) -> MoodleConnectionOut:
    """Token / Base-URL ändern. Mindestens ein Feld muss gesetzt sein."""
    if body.base_url is None and body.token is None:
        raise HTTPException(
            status_code=400,
            detail="Mindestens ein Feld (base_url, token) ist nötig.",
        )

    connection = _load_for_user(db=db, user=current_user, connection_id=connection_id)
    if body.base_url is not None:
        connection.base_url = str(body.base_url).rstrip("/")
    if body.token is not None:
        connection.token_encrypted = encrypt_secret(body.token)
    db.commit()
    db.refresh(connection)
    token_plain = body.token or _decrypt_or_500(connection)
    return _to_out(connection, token_plaintext=token_plain)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: int,
    current_user: User = Depends(require_permission("moodle:configure")),
    db: Session = Depends(get_db),
) -> Response:
    connection = _load_for_user(db=db, user=current_user, connection_id=connection_id)
    db.delete(connection)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Verbindungstest
# ---------------------------------------------------------------------------


@router.post("/{connection_id}/test", response_model=MoodleConnectionTestOut)
async def test_connection(
    connection_id: int,
    current_user: User = Depends(require_permission("moodle:configure")),
    db: Session = Depends(get_db),
) -> MoodleConnectionTestOut:
    """Ruft ``core_webservice_get_site_info`` auf.

    Antwortet mit 200 + ``ok: false`` bei Auth-/Netzwerkfehlern, damit
    das Frontend die Fehlermeldung im Form-State anzeigen kann (statt
    einer 4xx, die als generischer Toast auftauchen würde).
    """
    connection = _load_for_user(db=db, user=current_user, connection_id=connection_id)
    # Decryption failure indicates server-side encryption corruption
    # (rotated key, manual DB tamper) — that's a 500-class problem the
    # operator must see, not a friendly "token wrong" message in the
    # form. Other errors (auth, network) still come back as 200/ok=false
    # so the form can render the structured banner.
    token = _decrypt_or_500(connection)

    endpoint = connection.base_url.rstrip("/") + "/webservice/rest/server.php"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                endpoint,
                data={
                    "wstoken": token,
                    "moodlewsrestformat": "json",
                    "wsfunction": "core_webservice_get_site_info",
                },
            )
    except httpx.HTTPError as exc:
        return MoodleConnectionTestOut(
            ok=False,
            error=f"Verbindung fehlgeschlagen: {exc}",
        )

    if response.status_code >= 500:
        return MoodleConnectionTestOut(
            ok=False, error=f"Moodle-Fehler HTTP {response.status_code}"
        )
    if 400 <= response.status_code < 500:
        # Surface the real status so the operator can tell apart
        # "Token verboten" (401/403) from "Endpoint falsch" (404) and
        # "Rate-limit" (429) — without this branch all three render as
        # an opaque "Antwort war kein JSON".
        return MoodleConnectionTestOut(
            ok=False,
            error=(
                f"Moodle-Fehler HTTP {response.status_code} — "
                "Token-Berechtigung oder Endpoint prüfen."
            ),
        )
    try:
        data = response.json()
    except ValueError:
        return MoodleConnectionTestOut(ok=False, error="Antwort war kein JSON")

    if isinstance(data, dict) and "exception" in data:
        return MoodleConnectionTestOut(
            ok=False,
            error=data.get("message") or "unbekannter Fehler",
        )

    # Erfolg: Connection als getestet markieren.
    connection.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return MoodleConnectionTestOut(
        ok=True,
        site_name=data.get("sitename") if isinstance(data, dict) else None,
        site_url=data.get("siteurl") if isinstance(data, dict) else None,
        user_full_name=data.get("fullname") if isinstance(data, dict) else None,
    )
