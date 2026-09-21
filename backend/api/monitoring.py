"""Backend-Proxy für Frontend-Fehler (TF-864, ADR-012-Pattern aus `ratum`).

Der Browser kann den Specula-OTel-Collector nicht direkt erreichen (Flys privates 6PN-Netz,
analog `ratum`s ADR-012) — dieser Endpoint nimmt Frontend-Fehler entgegen und loggt sie als
ERROR mit `specula_signal_type=frontend_error`/`specula_origin=frontend`. Landet dadurch über
den root-logger-gebundenen `SpeculaLogHandler` (siehe `config/observability.py`, TF-865) im
selben Export-Pfad wie Backend-Fehler, aber unter einem EIGENEN Trigger-Signal (nicht
`unhandled_exception`): dieser Endpoint ist bewusst unauthentifiziert, eine einzelne IP könnte
sonst über die globale Rate-Limit-Grenze (`RateLimitMiddleware`, TF-492) fabrizierte
"unhandled exception"-Alarme in denselben Trigger fluten, der echte Backend-Crashes pagen soll.

BEWUSST unauthentifiziert (muss auch für nicht eingeloggte User funktionieren, z. B. Fehler auf
der Login-Seite) — abgesichert über die bereits global registrierte `RateLimitMiddleware`
(gilt für die gesamte API ausser `/health`), kein neuer Ratenlimit-Mechanismus nötig.

`sanitize_url()`/`strip_control_chars()` sind bewusst LOKAL implementiert statt aus
`specula-client-python` importiert (obwohl dort seit TF-892 verfügbar): `core/` wird
unverändert als Open-Source-Mirror veröffentlicht und darf nie hart von einem privaten Paket
abhängen (siehe `config/observability.py`s "package-fail-open" für Tracing/Logging). Für eine
Sicherheitskontrolle wie diese hier wäre Fail-Open aber keine akzeptable Degradierung, sondern
eine im öffentlichen Mirror-Build aktiv ausgelieferte Lücke (Log-Injection/Token-Leak über
einen unauthentifizierten Endpoint) — deshalb bleibt die Logik hier eigenständig, genau wie im
`ratum`-Original vor der Extraktion.
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

_SIGN_TOKEN_PATH = re.compile(r"/sign/[^/?#]+")
_CONTROL_CHARS = re.compile(r"[\r\n\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitize_url(url: str) -> str:
    """Redigiert `payload.url` vor dem Loggen (Defense-in-Depth).

    Das Frontend saniert bereits clientseitig, aber das Backend darf Client-Input nie
    vertrauen (alter gecachter Bundle, künftiger Bypass). Query-String pauschal strippen
    (kann Capability-Token tragen, z. B. `/verify-email?token=...`/`/reset-password?token=...`)
    und den `/sign/:token`-Pfad selbst redigieren (Signatur-Capability steckt dort direkt im
    Pfad, nicht im Query-String).
    """
    without_query = url.split("?", 1)[0].split("#", 1)[0]
    return _SIGN_TOKEN_PATH.sub("/sign/<redacted>", without_query)


def _strip_control_chars(text: str) -> str:
    """Neutralisiert Newlines/Steuerzeichen vor dem Loggen (Log-Injection-Schutz).

    Der Endpoint ist BEWUSST unauthentifiziert (s. o.) — ohne diese Sanitisierung könnte ein
    Aufrufer über Newlines in `message`/`stack` beliebige zusätzliche, gefälschte Log-Zeilen in
    einen zeilenorientierten Log-Formatter einschleusen (z. B. eine fabrizierte
    `... ERROR app.security: ...`-Zeile, die Forensik/Incident-Response untergräbt).
    """
    return _CONTROL_CHARS.sub(" ", text)


class ClientErrorIn(BaseModel):
    # Bewusst minimal (kein Breadcrumb-/Session-Tracking) — Payload-Grösse begrenzt
    # (max_length), damit der unauthentifizierte Endpoint nicht als Freitext-Abladeplatz
    # missbraucht werden kann.
    message: str = Field(max_length=2000)
    stack: str = Field(default="", max_length=8000)
    url: str = Field(max_length=2000)
    user_agent: str = Field(max_length=500, alias="userAgent")
    component_stack: str = Field(default="", max_length=4000, alias="componentStack")

    # extra="forbid": ein unauthentifizierter Endpoint sollte unbekannte Felder ablehnen statt
    # sie stillschweigend zu verwerfen — der konservativere Default.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ClientErrorAck(BaseModel):
    status: str = "accepted"


@router.post(
    "/client-errors",
    response_model=ClientErrorAck,
    status_code=status.HTTP_202_ACCEPTED,
)
def report_client_error(payload: ClientErrorIn) -> ClientErrorAck:
    logger.error(
        "Frontend-Fehler auf %s: %s\n%s",
        _sanitize_url(payload.url),
        _strip_control_chars(payload.message),
        _strip_control_chars(payload.stack),
        extra={
            "specula_signal_type": "frontend_error",
            "specula_origin": "frontend",
            "specula_user_agent": _strip_control_chars(payload.user_agent),
            "specula_component_stack": _strip_control_chars(payload.component_stack),
        },
    )
    return ClientErrorAck()
