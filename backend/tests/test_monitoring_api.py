"""Tests für den Frontend-Fehler-Proxy (TF-864, ``api.monitoring``, ADR-012-Pattern).

Unauthentifiziert by design (muss auch für nicht eingeloggte User funktionieren, z. B. Fehler
auf der Login-Seite) — wie ``test_legal_api.py`` brauchen diese Tests also keine Auth-Fixtures
oder DB-Overrides.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from api import monitoring
from main import app

app.include_router(monitoring.router)

client = TestClient(app)

ENDPOINT = "/api/v1/monitoring/client-errors"


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
