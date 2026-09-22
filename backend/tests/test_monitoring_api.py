"""Tests für die Frontend-Monitoring-Proxies (``api.monitoring``, ADR-012-Pattern):
Fehler-Reports (TF-864) und Session-Replay-Batches (TF-867).

Unauthentifiziert by design (muss auch für nicht eingeloggte User funktionieren, z. B. Fehler
auf der Login-Seite) — wie ``test_legal_api.py`` brauchen diese Tests also keine Auth-Fixtures
oder DB-Overrides.
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from api import monitoring
from main import app

app.include_router(monitoring.router)

client = TestClient(app)

ENDPOINT = "/api/v1/monitoring/client-errors"
REPLAY_ENDPOINT = "/api/v1/monitoring/session-replay"


def _replay_payload(**overrides) -> dict:
    payload = {
        "sessionId": "11111111-1111-1111-1111-111111111111",
        "samplingMode": "normal",
        "events": [{"type": 4, "data": {"href": "https://example.com/"}}],
    }
    payload.update(overrides)
    return payload


def test_client_error_endpoint_works_without_auth() -> None:
    response = client.post(
        ENDPOINT,
        json={
            "message": "boom",
            "stack": "",
            "url": "https://example.com/login",
            "userAgent": "x",
        },
    )

    assert response.status_code == 202


def test_client_error_endpoint_ignores_a_garbage_authorization_header() -> None:
    """Stärker als "keine Auth-Header gesendet": beweist, dass die Route keine
    Auth-Dependency deklariert — ein abgelaufener/kaputter Bearer-Token darf nicht zu 401 führen.
    """
    response = client.post(
        ENDPOINT,
        json={
            "message": "boom",
            "stack": "",
            "url": "https://example.com/login",
            "userAgent": "x",
        },
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 202


def test_client_error_endpoint_logs_frontend_signal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="api.monitoring"):
        response = client.post(
            ENDPOINT,
            json={
                "message": "TypeError: x is undefined",
                "stack": "at foo (bundle.js:1:1)",
                "url": "https://example.com/dashboard",
                "userAgent": "pytest-agent",
            },
        )

    assert response.status_code == 202
    # Eigenes Signal statt `unhandled_exception`: der unauthentifizierte Frontend-Proxy darf
    # nicht in denselben Collector-Trigger wie echte Backend-Crashes fallen.
    record = next(
        r
        for r in caplog.records
        if getattr(r, "specula_signal_type", None) == "frontend_error"
    )
    assert record.specula_origin == "frontend"
    assert "TypeError: x is undefined" in record.getMessage()


def test_client_error_endpoint_logs_user_agent_and_component_stack(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # component_stack ist bei React-Render-Fehlern das wertvollste Feld, user_agent hilft beim
    # Eingrenzen browser-spezifischer Fehler — beide müssen als specula_*-Extra am Log-Record
    # ankommen (und damit über den SpeculaLogHandler-Export exportiert werden).
    with caplog.at_level(logging.ERROR, logger="api.monitoring"):
        client.post(
            ENDPOINT,
            json={
                "message": "boom",
                "stack": "",
                "url": "https://example.com/dashboard",
                "userAgent": "Mozilla/5.0 pytest",
                "componentStack": "at Dashboard\nat App",
            },
        )

    record = next(
        r
        for r in caplog.records
        if getattr(r, "specula_signal_type", None) == "frontend_error"
    )
    assert record.specula_user_agent == "Mozilla/5.0 pytest"
    assert "at Dashboard" in record.specula_component_stack


def test_client_error_endpoint_redacts_query_string_tokens_from_logged_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # /reset-password trägt ein Live-Capability-Token im Query-String — darf nicht ungefiltert
    # an den ERROR-Export (SpeculaLogHandler) gehen.
    with caplog.at_level(logging.ERROR, logger="api.monitoring"):
        client.post(
            ENDPOINT,
            json={
                "message": "boom",
                "stack": "",
                "url": "https://example.com/reset-password?token=super-secret",
                "userAgent": "pytest-agent",
            },
        )

    record = next(
        r
        for r in caplog.records
        if getattr(r, "specula_signal_type", None) == "frontend_error"
    )
    assert "super-secret" not in record.getMessage()
    assert "https://example.com/reset-password" in record.getMessage()


def test_client_error_endpoint_redacts_userinfo_credentials_from_logged_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # TF-895: Userinfo-Credentials in der URL-Autorität (https://user:pass@host/...) sind ein
    # Log-Leak-Vektor, den Query-String- und /sign/:token-Redacting allein nicht abdecken.
    with caplog.at_level(logging.ERROR, logger="api.monitoring"):
        client.post(
            ENDPOINT,
            json={
                "message": "boom",
                "stack": "",
                "url": "https://user:secret@example.com/dashboard",
                "userAgent": "pytest-agent",
            },
        )

    record = next(
        r
        for r in caplog.records
        if getattr(r, "specula_signal_type", None) == "frontend_error"
    )
    assert "secret" not in record.getMessage()
    assert "https://example.com/dashboard" in record.getMessage()


def test_client_error_endpoint_redacts_userinfo_with_at_sign_embedded_in_password(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Parser-Differential-Regressionstest: ein Passwort mit eingebettetem "@" darf nicht nur
    # bis zum ERSTEN "@" redigiert werden (das würde den Rest des Passworts als scheinbaren
    # Host im Log stehen lassen) — Browser/WHATWG-URL-Parser trennen die Autorität am
    # LETZTEN "@" vor dem ersten "/", das muss api.monitoring auch tun.
    with caplog.at_level(logging.ERROR, logger="api.monitoring"):
        client.post(
            ENDPOINT,
            json={
                "message": "boom",
                "stack": "",
                "url": "https://user:p@ss@example.com/path",
                "userAgent": "pytest-agent",
            },
        )

    record = next(
        r
        for r in caplog.records
        if getattr(r, "specula_signal_type", None) == "frontend_error"
    )
    rendered = record.getMessage()
    assert "p@ss" not in rendered
    assert "ss@example.com" not in rendered
    assert "https://example.com/path" in rendered


def test_client_error_endpoint_redacts_sign_token_path_from_logged_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # /sign/:token trägt die Signatur-Capability direkt im Pfad, nicht im Query-String.
    with caplog.at_level(logging.ERROR, logger="api.monitoring"):
        client.post(
            ENDPOINT,
            json={
                "message": "boom",
                "stack": "",
                "url": "https://example.com/sign/abc123def",
                "userAgent": "pytest-agent",
            },
        )

    record = next(
        r
        for r in caplog.records
        if getattr(r, "specula_signal_type", None) == "frontend_error"
    )
    assert "abc123def" not in record.getMessage()
    assert "https://example.com/sign/<redacted>" in record.getMessage()


def test_client_error_endpoint_strips_newlines_to_prevent_log_injection(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Ohne Sanitisierung könnte ein Aufrufer über Newlines in message/stack eine gefälschte
    # zusätzliche Log-Zeile einschleusen (z. B. eine fabrizierte "ERROR app.security: ..."-Zeile).
    with caplog.at_level(logging.ERROR, logger="api.monitoring"):
        client.post(
            ENDPOINT,
            json={
                "message": "boom\nERROR app.security: fake admin login from 1.2.3.4",
                "stack": "at foo\r\nat bar",
                "url": "https://example.com/",
                "userAgent": "pytest-agent",
            },
        )

    record = next(
        r
        for r in caplog.records
        if getattr(r, "specula_signal_type", None) == "frontend_error"
    )
    rendered = record.getMessage()
    assert "fake admin login" in rendered
    assert not any(
        line.strip().startswith("ERROR app.security") for line in rendered.splitlines()
    )
    assert "\r" not in rendered


def test_client_error_endpoint_rejects_oversized_payload() -> None:
    response = client.post(
        ENDPOINT,
        json={
            "message": "x" * 10_000,
            "stack": "",
            "url": "https://example.com/",
            "userAgent": "x",
        },
    )

    assert response.status_code == 422


def test_client_error_endpoint_rejects_missing_fields() -> None:
    response = client.post(ENDPOINT, json={"message": "boom"})

    assert response.status_code == 422


def test_client_error_endpoint_rejects_unknown_fields() -> None:
    # extra="forbid": ein unauthentifizierter Endpoint sollte unbekannte Felder ablehnen statt
    # sie stillschweigend zu verwerfen.
    response = client.post(
        ENDPOINT,
        json={
            "message": "boom",
            "stack": "",
            "url": "https://example.com/",
            "userAgent": "x",
            "unexpectedField": "sneaky",
        },
    )

    assert response.status_code == 422


# --- /session-replay (TF-867) ---
#
# Nimmt gebatchte rrweb-Events vom Frontend entgegen und reicht sie als OTLP-Logs an
# OTEL_EXPORTER_ENDPOINT weiter (Browser kann den Collector nicht direkt erreichen, siehe
# Moduldoc). Unauthentifiziert wie /client-errors, aus demselben Grund.


def test_session_replay_endpoint_works_without_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_ENDPOINT", raising=False)
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)

    response = client.post(REPLAY_ENDPOINT, json=_replay_payload())

    assert response.status_code == 202


def test_session_replay_endpoint_does_not_forward_when_otel_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_ENDPOINT", raising=False)
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)

    with respx.mock(assert_all_called=False) as mock:
        mock.post("https://collector.example.com/v1/logs").mock(
            return_value=httpx.Response(200)
        )
        response = client.post(REPLAY_ENDPOINT, json=_replay_payload())

    assert response.status_code == 202
    assert mock.calls.call_count == 0


def test_session_replay_endpoint_forwards_batch_as_otlp_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://collector.example.com")
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", "team-key-123")

    with respx.mock(assert_all_called=True) as mock:
        route = mock.post("https://collector.example.com/v1/logs").mock(
            return_value=httpx.Response(200)
        )
        response = client.post(
            REPLAY_ENDPOINT,
            json=_replay_payload(
                sessionId="22222222-2222-2222-2222-222222222222",
                samplingMode="error",
                correlationId="trace-abc",
                events=[
                    {"type": 4, "data": {"href": "https://example.com/a"}},
                    {"type": 3, "data": {"source": 0}},
                ],
            ),
        )

    assert response.status_code == 202
    request = route.calls.last.request
    assert request.headers["Authorization"] == "team-key-123"
    body = json.loads(request.content)
    resource_attrs = {
        a["key"]: a["value"]["stringValue"]
        for a in body["resourceLogs"][0]["resource"]["attributes"]
    }
    assert resource_attrs["rum.sessionId"] == "22222222-2222-2222-2222-222222222222"

    scope_logs = body["resourceLogs"][0]["scopeLogs"][0]
    assert scope_logs["scope"]["name"] == "rum.rr-web"
    log_records = scope_logs["logRecords"]
    assert len(log_records) == 2

    first_attrs = {
        a["key"]: a["value"]["stringValue"] for a in log_records[0]["attributes"]
    }
    assert first_attrs["rr-web.event"] == "1"
    assert first_attrs["rr-web.offset"] == "0"
    assert first_attrs["rr-web.chunk"] == "1"
    assert first_attrs["rr-web.total-chunks"] == "1"
    assert first_attrs["specula.sampling_mode"] == "error"
    assert first_attrs["specula.correlation_id"] == "trace-abc"
    assert json.loads(log_records[0]["body"]["stringValue"]) == {
        "type": 4,
        "data": {"href": "https://example.com/a"},
    }
    second_attrs = {
        a["key"]: a["value"]["stringValue"] for a in log_records[1]["attributes"]
    }
    assert second_attrs["rr-web.offset"] == "1"


def test_session_replay_endpoint_omits_correlation_id_attribute_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://collector.example.com")
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", "team-key-123")

    with respx.mock() as mock:
        route = mock.post("https://collector.example.com/v1/logs").mock(
            return_value=httpx.Response(200)
        )
        client.post(REPLAY_ENDPOINT, json=_replay_payload())

    body = json.loads(route.calls.last.request.content)
    attrs = {
        a["key"]
        for a in body["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]["attributes"]
    }
    assert "specula.correlation_id" not in attrs


def test_session_replay_endpoint_strips_trailing_slash_from_otel_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://collector.example.com/")
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", "team-key-123")

    with respx.mock() as mock:
        mock.post("https://collector.example.com/v1/logs").mock(
            return_value=httpx.Response(200)
        )
        response = client.post(REPLAY_ENDPOINT, json=_replay_payload())

    assert response.status_code == 202


def test_session_replay_endpoint_swallows_forwarding_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://collector.example.com")
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", "team-key-123")

    with (
        caplog.at_level(logging.ERROR, logger="api.monitoring"),
        respx.mock() as mock,
    ):
        mock.post("https://collector.example.com/v1/logs").mock(
            return_value=httpx.Response(500)
        )
        response = client.post(REPLAY_ENDPOINT, json=_replay_payload())

    # Ein fehlgeschlagener Forward darf den Frontend-Aufrufer nie beeintraechtigen (Ack bleibt
    # 202) -- muss aber serverseitig sichtbar bleiben, unter einem eigenen Signal (nicht dem
    # Default-Trigger, der sonst echte Backend-Crashes pagen soll).
    assert response.status_code == 202
    record = next(r for r in caplog.records if "Session-Replay" in r.getMessage())
    assert record.specula_signal_type == "session_replay_forward_failed"
    assert record.specula_origin == "backend"


def test_session_replay_endpoint_swallows_payload_build_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Separates except vom Netzwerk-Call (siehe monitoring.py): ein Bug beim Payload-Aufbau ist
    # kein Zustellfehler und muss trotzdem fail-open bleiben, aber unter einer eigenen Meldung
    # sichtbar werden statt unter derselben "Collector down"-Meldung zu verschwinden.
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://collector.example.com")
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", "team-key-123")

    def _boom(_payload):
        raise TypeError("boom")

    monkeypatch.setattr(monitoring, "_build_otlp_replay_payload", _boom)

    with (
        caplog.at_level(logging.ERROR, logger="api.monitoring"),
        respx.mock(assert_all_called=False) as mock,
    ):
        mock.post("https://collector.example.com/v1/logs").mock(
            return_value=httpx.Response(200)
        )
        response = client.post(REPLAY_ENDPOINT, json=_replay_payload())

    assert response.status_code == 202
    assert mock.calls.call_count == 0
    assert any("OTLP-Payload-Aufbau" in r.getMessage() for r in caplog.records)


def test_session_replay_endpoint_strips_control_chars_from_logged_session_id(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Log-Injection-Regressionstest (analog test_client_error_endpoint_strips_newlines_...):
    # session_id ist auf einem unauthentifizierten Endpoint frei vom Aufrufer waehlbar und wird
    # im Fail-open-Pfad geloggt -- ohne Sanitisierung koennte ein Aufrufer darueber gefaelschte
    # zusaetzliche Log-Zeilen einschleusen.
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://collector.example.com")
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", "team-key-123")

    with (
        caplog.at_level(logging.ERROR, logger="api.monitoring"),
        respx.mock() as mock,
    ):
        mock.post("https://collector.example.com/v1/logs").mock(
            return_value=httpx.Response(500)
        )
        response = client.post(
            REPLAY_ENDPOINT,
            json=_replay_payload(
                sessionId="boom\nERROR app.security: fake admin login from 1.2.3.4"
            ),
        )

    assert response.status_code == 202
    record = next(
        r for r in caplog.records if "Session-Replay-Weiterleitung" in r.getMessage()
    )
    rendered = record.getMessage()
    assert "\n" not in rendered
    assert not any(
        line.strip().startswith("ERROR app.security") for line in rendered.splitlines()
    )


def test_session_replay_endpoint_redacts_capability_token_from_meta_event_href(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://collector.example.com")
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", "team-key-123")

    with respx.mock() as mock:
        route = mock.post("https://collector.example.com/v1/logs").mock(
            return_value=httpx.Response(200)
        )
        response = client.post(
            REPLAY_ENDPOINT,
            json=_replay_payload(
                events=[
                    {
                        "type": 4,
                        "data": {
                            "href": "https://example.com/auth/reset-password/confirm?token=super-secret",
                            "width": 1024,
                            "height": 768,
                        },
                    }
                ]
            ),
        )

    assert response.status_code == 202
    body = json.loads(route.calls.last.request.content)
    log_record = body["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
    event_body = json.loads(log_record["body"]["stringValue"])
    assert (
        event_body["data"]["href"] == "https://example.com/auth/reset-password/confirm"
    )
    assert event_body["data"]["width"] == 1024
    assert "super-secret" not in log_record["body"]["stringValue"]


def test_session_replay_endpoint_warns_on_partial_otel_config_in_production(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Ein rotiertes/vergessenes Secret-Paar (nur eines von beiden gesetzt) darf in
    # staging/production nicht lautlos Session-Replay-Daten verwerfen.
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", "https://collector.example.com")
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)

    with caplog.at_level(logging.WARNING, logger="api.monitoring"):
        response = client.post(REPLAY_ENDPOINT, json=_replay_payload())

    assert response.status_code == 202
    assert any(
        r.levelno == logging.WARNING and "OTel nicht konfiguriert" in r.getMessage()
        for r in caplog.records
    )


def test_session_replay_endpoint_does_not_warn_when_otel_unset_in_development(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_ENDPOINT", raising=False)
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)

    with caplog.at_level(logging.WARNING, logger="api.monitoring"):
        response = client.post(REPLAY_ENDPOINT, json=_replay_payload())

    assert response.status_code == 202
    assert not any(r.levelno == logging.WARNING for r in caplog.records)


def test_session_replay_endpoint_rejects_missing_fields() -> None:
    response = client.post(REPLAY_ENDPOINT, json={"sessionId": "s"})

    assert response.status_code == 422


def test_session_replay_endpoint_rejects_unknown_fields() -> None:
    response = client.post(
        REPLAY_ENDPOINT, json=_replay_payload(unexpectedField="sneaky")
    )

    assert response.status_code == 422


def test_session_replay_endpoint_rejects_invalid_sampling_mode() -> None:
    response = client.post(REPLAY_ENDPOINT, json=_replay_payload(samplingMode="turbo"))

    assert response.status_code == 422


def test_session_replay_endpoint_rejects_empty_events() -> None:
    response = client.post(REPLAY_ENDPOINT, json=_replay_payload(events=[]))

    assert response.status_code == 422


def test_session_replay_endpoint_rejects_too_many_events() -> None:
    events = [{"type": 3, "data": {"i": i}} for i in range(151)]

    response = client.post(REPLAY_ENDPOINT, json=_replay_payload(events=events))

    assert response.status_code == 422


def test_session_replay_endpoint_rejects_oversized_single_event() -> None:
    huge_event = {"type": 3, "data": {"payload": "x" * 400_000}}

    response = client.post(REPLAY_ENDPOINT, json=_replay_payload(events=[huge_event]))

    assert response.status_code == 422


def test_session_replay_endpoint_accepts_event_at_exact_byte_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Off-by-One-Regressionstest: ein Event GENAU an der Byte-Grenze darf nicht faelschlich
    # abgelehnt werden.
    monkeypatch.delenv("OTEL_EXPORTER_ENDPOINT", raising=False)
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)

    base_event = {"type": 3, "data": {"payload": ""}}
    padding = monitoring._MAX_REPLAY_EVENT_BYTES - len(json.dumps(base_event))
    exact_event = {"type": 3, "data": {"payload": "x" * padding}}
    assert len(json.dumps(exact_event)) == monitoring._MAX_REPLAY_EVENT_BYTES

    response = client.post(REPLAY_ENDPOINT, json=_replay_payload(events=[exact_event]))

    assert response.status_code == 202


def test_session_replay_endpoint_rejects_oversized_batch_total() -> None:
    # Kein Einzel-Event ueber dem Limit, aber die Summe ueberschreitet _MAX_REPLAY_BATCH_BYTES --
    # ohne dieses Gesamtlimit waere ein bis zu ~45 MB grosser Request an diesem
    # unauthentifizierten Endpoint moeglich (siehe Moduldoc).
    events = [{"type": 3, "data": {"payload": "x" * 200_000}} for _ in range(30)]

    response = client.post(REPLAY_ENDPOINT, json=_replay_payload(events=events))

    assert response.status_code == 422
