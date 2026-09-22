"""Backend-Proxys für Frontend-Monitoring (ADR-012-Pattern aus `ratum`):
Fehler-Reports (`/client-errors`, TF-864) und Session-Replay-Batches (`/session-replay`, TF-867).

Der Browser kann den Specula-OTel-Collector nicht direkt erreichen (Flys privates 6PN-Netz,
analog `ratum`s ADR-012) — `/client-errors` nimmt Frontend-Fehler entgegen und loggt sie als
ERROR mit `specula_signal_type=frontend_error`/`specula_origin=frontend`. Landet dadurch über
den root-logger-gebundenen `SpeculaLogHandler` (siehe `config/observability.py`, TF-865) im
selben Export-Pfad wie Backend-Fehler, aber unter einem EIGENEN Trigger-Signal (nicht
`unhandled_exception`): dieser Endpoint ist bewusst unauthentifiziert, eine einzelne IP könnte
sonst über die globale Rate-Limit-Grenze (`RateLimitMiddleware`, TF-492) fabrizierte
"unhandled exception"-Alarme in denselben Trigger fluten, der echte Backend-Crashes pagen soll.

`/session-replay` nimmt gebatchte rrweb-Events entgegen (Frontend-Wrapper: `utils/sessionReplay.ts`,
TF-867) und baut daraus einen OTLP-`/v1/logs`-Request für `OTEL_EXPORTER_ENDPOINT`
(`_build_otlp_replay_payload()`; jedes rrweb-Event landet unverändert als Log-Body, wird aber in
eine `resourceLogs`/`scopeLogs`-Hülle mit `rr-web.*`/`specula.*`-Attributen eingebettet -- kein
reiner Pass-Through), mit `SPECULA_TEAM_API_KEY` als `Authorization`-Header -- der Browser kennt
diesen Team-Key nicht (genau wie er den Collector selbst nicht erreicht), nur das Backend darf ihn
verwenden. Das Basis-Payload-Schema (Resource-Attribut `rum.sessionId`, Scope `rum.rr-web`,
Log-Attribute `rr-web.*`) ist NICHT selbst designt, sondern das von HyperDX/ClickStack nativ
erwartete Format für Session-Replay-Ingestion (siehe `specula`-Repo, TF-859
"ClickHouse-Ingestion-Pfad", live gegen Fly-Prod verifiziert per
`otel-collector/scripts/verify_session_replay.py` -- das deckt nur das Wire-Format ab, NICHT die
End-to-End-Player-Verifikation dieses Endpoints selbst, siehe TF-867 AC4); `specula.sampling_mode`/
`specula.correlation_id` sind dagegen eigene, nicht vom Vendor-Schema vorgegebene Zusatzattribute.
Jedes rrweb-Event wird unchunked als ein Log-Record gesendet (`rr-web.chunk`/`rr-web.total-chunks`
konstant `"1"`), da der Frontend-Wrapper bereits in handlichen Batches sendet statt einzelner
Riesen-Events. Fail-open wie die restliche Observability-Kette (`config/observability.py`):
fehlt `OTEL_EXPORTER_ENDPOINT`/`SPECULA_TEAM_API_KEY` (z. B. lokal/OSS-Build ohne Collector-
Zugang), wird der Batch quittiert, aber nicht weitergeleitet -- in `staging`/`production` dabei
laut (WARNING, analog `config/observability.py`s "TF-359 carryover"), da ein nur TEILWEISE
gesetztes Secret-Paar (z. B. nach einer Rotation) sonst tagelang lautlos Session-Replay-Daten
verwirft; schlägt der Forward selbst fehl (Netzwerk/Collector-Fehler), bleibt die Ack-Antwort an
den Frontend-Aufrufer trotzdem 202 -- ein Zustellfehler an den Collector darf den rrweb-Recorder
im Browser nie stören (analog `errorReporting.ts`s "wirft nie"-Vertrag). Ein Bug beim
Payload-Aufbau selbst (`_build_otlp_replay_payload()`) wird bewusst SEPARAT gefangen/geloggt --
sonst wäre ein eigener Code-Fehler von aussen nicht von einem simplen Collector-Ausfall zu
unterscheiden.

BEIDE Endpoints BEWUSST unauthentifiziert (müssen auch für nicht eingeloggte User funktionieren,
z. B. Fehler/Session-Replay auf der Login-Seite) — abgesichert über die bereits global
registrierte `RateLimitMiddleware` (gilt für die gesamte API ausser `/health`), kein neuer
Ratenlimit-Mechanismus nötig. Payload-Grössen sind deshalb bei beiden begrenzt (siehe
`ClientErrorIn`/`SessionReplayBatchIn`), damit die unauthentifizierten Endpoints nicht als
Freitext-/Bulk-Abladeplatz missbraucht werden können -- NICHT gleich eng: `ClientErrorIn` deckelt
auf ~16 KB, `SessionReplayBatchIn` (rrweb-Snapshots sind naturgemäss grösser) auf ein Gesamtlimit
über den Batch (`_MAX_REPLAY_BATCH_BYTES`) zusätzlich zum Einzel-Event-Limit -- ohne dieses
Gesamtlimit würde `_MAX_REPLAY_EVENTS * _MAX_REPLAY_EVENT_BYTES` allein rechnerisch bis zu ~45 MB
pro unauthentifiziertem Request erlauben.

`sanitize_url()`/`strip_control_chars()` sind bewusst LOKAL implementiert statt aus
`specula-client-python` importiert (obwohl dort seit TF-892/TF-895 verfügbar): `core/` wird
unverändert als Open-Source-Mirror veröffentlicht und darf nie hart von einem privaten Paket
abhängen (siehe `config/observability.py`s "package-fail-open" für Tracing/Logging). Für eine
Sicherheitskontrolle wie diese hier wäre Fail-Open aber keine akzeptable Degradierung, sondern
eine im öffentlichen Mirror-Build aktiv ausgelieferte Lücke (Log-Injection/Token-Leak über
einen unauthentifizierten Endpoint) — deshalb bleibt die Logik hier eigenständig, genau wie im
`ratum`-Original vor der Extraktion. Der OTLP-Payload-Aufbau für `/session-replay` betrifft
dagegen keine Sicherheitskontrolle (nur ein fest verdrahtetes Wire-Format), bleibt aber aus
demselben Grund lokal in dieser Datei statt aus `specula_client` importiert zu werden -- letzteres
kennt (Stand TF-892) ohnehin keinen generischen "sende rohes OTLP"-Helper, nur den strukturierten
Python-`logging`-Adapter.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Literal

import httpx
from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

# Grenzwerte fuer /session-replay: der Frontend-Wrapper (utils/sessionReplay.ts) batcht schon auf
# max. 100 Events pro Flush -- 150 lassen etwas Kopfraum, ohne den unauthentifizierten Endpoint
# unbegrenzt zu lassen. 300 KB pro Event deckt ein rrweb-Full-Snapshot-Event einer normal
# komplexen Seite ab; ein Vielfaches davon ist eher Missbrauch als ein legitimer Snapshot.
_MAX_REPLAY_EVENTS = 150
_MAX_REPLAY_EVENT_BYTES = 300_000
# Ergaenzt die Einzel-Event-Grenze um ein Gesamtlimit: ohne dieses erlaubt
# `_MAX_REPLAY_EVENTS * _MAX_REPLAY_EVENT_BYTES` bis zu ~45 MB in einem einzigen Request an einen
# unauthentifizierten Endpoint. 5 MB deckt den Normalfall (Frontend batcht auf 100 Events, i. d. R.
# deutlich kleiner als das Einzel-Event-Limit, plus gelegentlich ein Full-Snapshot) grosszuegig ab.
_MAX_REPLAY_BATCH_BYTES = 5_000_000
_REPLAY_SERVICE_NAME = "examcraft-frontend"
_META_EVENT_TYPE = 4

_SIGN_TOKEN_PATH = re.compile(r"/sign/[^/?#]+")
_CONTROL_CHARS = re.compile(r"[\r\n\x00-\x08\x0b\x0c\x0e-\x1f]")

# Matcht ein optionales Schema gefolgt von `user[:pass]@` in der URL-Autorität (TF-895).
# `[^/]*` (statt `[^/@]*`) ist bewusst gewählt: greedy über ALLE "@" hinweg bis zum LETZTEN
# "@" vor dem ersten "/" — genau wie WHATWG-URL-Parser (Browser) die Autorität trennen. Ein
# erster Versuch mit `[^/@]*` (stoppt am ERSTEN "@") liess ein Passwort mit eingebettetem "@"
# (z. B. "user:p@ss@host") nur bis zum ersten "@" redigieren und "ss@host" unredigiert als
# scheinbaren Host im Log stehen — ein Parser-Differential-Bug derselben Klasse wie die
# Browser-Obfuskationstechnik "user@fake.example@real-host.example". Der Pfad bleibt trotzdem
# geschützt: `[^/]*` kann "/" nie konsumieren, ein "@" NACH dem ersten "/" (z. B.
# "/path@2x.png") liegt also ausserhalb des möglichen Matches.
_USERINFO = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*://)?[^/]*@")


def _sanitize_url(url: str) -> str:
    """Redigiert `payload.url` vor dem Loggen (Defense-in-Depth).

    Das Frontend saniert bereits clientseitig, aber das Backend darf Client-Input nie
    vertrauen (alter gecachter Bundle, künftiger Bypass). Query-String pauschal strippen
    (kann Capability-Token tragen, z. B. `/verify-email?token=...`/`/reset-password?token=...`),
    Userinfo-Credentials aus der URL-Autorität entfernen (`https://user:pass@host/...`,
    TF-895) und den `/sign/:token`-Pfad selbst redigieren (Signatur-Capability steckt dort
    direkt im Pfad, nicht im Query-String).
    """
    without_query = url.split("?", 1)[0].split("#", 1)[0]
    without_userinfo = _USERINFO.sub(r"\1", without_query)
    return _SIGN_TOKEN_PATH.sub("/sign/<redacted>", without_userinfo)


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


class SessionReplayBatchIn(BaseModel):
    # Deckt sich 1:1 mit specula-client-js' `SessionReplayEventBatch` (siehe Moduldoc) -- eigenes
    # Modell statt Import, s. Moduldoc-Begruendung.
    session_id: str = Field(max_length=100, alias="sessionId")
    correlation_id: str | None = Field(
        default=None, max_length=200, alias="correlationId"
    )
    sampling_mode: Literal["normal", "error"] = Field(alias="samplingMode")
    # rrweb-Events sind beliebig verschachteltes JSON (DOM-Snapshots, Mutations, ...) -- dieser
    # Endpoint muss ihre Struktur nicht verstehen, nur unveraendert als Log-Body weiterreichen.
    events: list[dict[str, Any]] = Field(min_length=1, max_length=_MAX_REPLAY_EVENTS)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("events")
    @classmethod
    def _bound_events(cls, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Erzwingt sowohl das Einzel-Event- als auch das Gesamt-Batch-Limit (siehe Moduldoc) --
        in einer Schleife, um jedes Event nur einmal zu serialisieren statt eines separaten
        Gesamt-Serialisierungs-Durchlaufs."""
        total_bytes = 0
        for event in events:
            event_bytes = len(json.dumps(event))
            if event_bytes > _MAX_REPLAY_EVENT_BYTES:
                raise ValueError(
                    f"Ein rrweb-Event darf serialisiert maximal {_MAX_REPLAY_EVENT_BYTES} "
                    "Bytes gross sein."
                )
            total_bytes += event_bytes
        if total_bytes > _MAX_REPLAY_BATCH_BYTES:
            raise ValueError(
                f"Der gesamte Event-Batch darf serialisiert maximal {_MAX_REPLAY_BATCH_BYTES} "
                "Bytes gross sein."
            )
        return events


class SessionReplayAck(BaseModel):
    status: Literal["accepted"] = "accepted"


def _sanitized_event_body(event: dict[str, Any]) -> str:
    """Serialisiert ein rrweb-Event fuer den OTLP-Log-Body.

    rrweb-Meta-Events (`type: 4`) tragen `data.href` mit der vollen Seiten-URL inkl.
    Query-String/Fragment -- kann wie `ClientErrorIn.url` ein Capability-Token tragen (z. B.
    `/auth/reset-password/confirm?token=...`). Der Frontend-Wrapper filtert das bereits
    client-seitig (`sessionReplay.ts`s `sanitizeMetaHref()`), diese Funktion ist Defense-in-Depth
    analog `_sanitize_url()` bei `/client-errors` -- das Backend darf Client-Input nie vertrauen
    (alter gecachter Bundle, kuenftiger Bypass).
    """
    if event.get("type") == _META_EVENT_TYPE:
        data = event.get("data")
        if isinstance(data, dict) and isinstance(data.get("href"), str):
            event = {**event, "data": {**data, "href": _sanitize_url(data["href"])}}
    return json.dumps(event)


def _build_otlp_replay_payload(batch: SessionReplayBatchIn) -> dict[str, Any]:
    """Baut den OTLP-`/v1/logs`-Request fuer einen rrweb-Event-Batch (siehe Moduldoc fuer das
    von HyperDX/ClickStack erwartete Attribut-Schema)."""
    now_ns = str(time.time_ns())
    log_records = []
    for offset, event in enumerate(batch.events):
        attributes = [
            {"key": "rr-web.event", "value": {"stringValue": "1"}},
            {"key": "rr-web.offset", "value": {"stringValue": str(offset)}},
            # Kein tatsaechliches Chunking (siehe Moduldoc): jedes Event ist bereits ein
            # vollstaendiger Log-Body, "1"/"1" markiert es als sein eigener, einziger Chunk.
            {"key": "rr-web.chunk", "value": {"stringValue": "1"}},
            {"key": "rr-web.total-chunks", "value": {"stringValue": "1"}},
            {
                "key": "specula.sampling_mode",
                "value": {"stringValue": batch.sampling_mode},
            },
        ]
        if batch.correlation_id:
            attributes.append(
                {
                    "key": "specula.correlation_id",
                    "value": {"stringValue": batch.correlation_id},
                }
            )
        log_records.append(
            {
                "timeUnixNano": now_ns,
                "body": {"stringValue": _sanitized_event_body(event)},
                "attributes": attributes,
            }
        )
    return {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        {
                            "key": "service.name",
                            "value": {"stringValue": _REPLAY_SERVICE_NAME},
                        },
                        {
                            "key": "rum.sessionId",
                            "value": {"stringValue": batch.session_id},
                        },
                    ]
                },
                "scopeLogs": [
                    {"scope": {"name": "rum.rr-web"}, "logRecords": log_records}
                ],
            }
        ]
    }


@router.post(
    "/session-replay",
    response_model=SessionReplayAck,
    status_code=status.HTTP_202_ACCEPTED,
)
async def report_session_replay(payload: SessionReplayBatchIn) -> SessionReplayAck:
    environment = os.getenv("ENVIRONMENT", "development")
    endpoint = os.getenv("OTEL_EXPORTER_ENDPOINT")
    team_api_key = os.getenv("SPECULA_TEAM_API_KEY")

    if not (endpoint and team_api_key):
        # Fail-open (siehe Moduldoc) -- aber laut in staging/production (analog
        # config/observability.py's "TF-359 carryover"): ein nur TEILWEISE gesetztes Secret-Paar
        # (z. B. nach einer Rotation, bei der nur eines der beiden Secrets aktualisiert wurde --
        # dieses Projekt hat genau dieses Muster mehrfach produktiv getroffen, siehe TF-776/
        # TF-796/TF-821) wuerde sonst tagelang lautlos Session-Replay-Daten verwerfen.
        if environment in ("staging", "production"):
            logger.warning(
                "[monitoring] Session-Replay-Batch verworfen (OTel nicht konfiguriert: "
                "otel_exporter_endpoint_set=%s, specula_team_api_key_set=%s)",
                bool(endpoint),
                bool(team_api_key),
            )
        return SessionReplayAck()

    try:
        otlp_payload = _build_otlp_replay_payload(payload)
    except Exception:
        # Separat vom Netzwerk-Call unten gefangen: ein Bug in _build_otlp_replay_payload() ist
        # kein Zustellfehler und soll nicht unter derselben "Collector down"-Meldung verschwinden.
        logger.error(
            "[monitoring] OTLP-Payload-Aufbau fuer Session-Replay fehlgeschlagen "
            "(sessionId=%s) -- eigener Bug, kein Netzwerkfehler",
            _strip_control_chars(payload.session_id),
            exc_info=True,
        )
        return SessionReplayAck()

    try:
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            response = await http_client.post(
                f"{endpoint.rstrip('/')}/v1/logs",
                headers={"Authorization": team_api_key},
                json=otlp_payload,
            )
        response.raise_for_status()
    except httpx.HTTPError:
        # Fail-open (siehe Moduldoc): ein Zustellfehler an den Collector darf die Ack-Antwort
        # an den Frontend-Aufrufer nie beeintraechtigen, muss aber serverseitig sichtbar
        # bleiben (analog specula_client.logging._send_to_specula()). Eigenes Signal (nicht der
        # Default-Trigger): siehe Moduldoc-Begruendung fuer `/client-errors`s
        # `specula_signal_type=frontend_error` -- dieselbe Flut-Gefahr gilt hier fuer
        # Collector-Ausfaelle.
        logger.error(
            "[monitoring] Session-Replay-Weiterleitung an %s fehlgeschlagen "
            "(sessionId=%s, %d Events verworfen)",
            endpoint,
            _strip_control_chars(payload.session_id),
            len(payload.events),
            exc_info=True,
            extra={
                "specula_signal_type": "session_replay_forward_failed",
                "specula_origin": "backend",
            },
        )
    return SessionReplayAck()
