"""Tests for ObservabilityContextMiddleware (TF-865).

Replaces the retired middleware/sentry_context.py — same responsibility
(attach user + request context for triage), now as OTel span attributes
instead of a Sentry scope. No dedicated test existed for the Sentry version;
this is new coverage for the migration, including the PII-scrubbing
requirement from the ticket's "Scrubber-Modul statt custom EventScrubber"
scope.
"""

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import middleware.observability_context as observability_context_module
from config.observability import EXTRA_PII_DENYLIST
from middleware.observability_context import ObservabilityContextMiddleware


class _FakeSpan:
    """Records set_attribute() calls instead of talking to a real exporter."""

    def __init__(self):
        self.attributes: dict[str, object] = {}

    def set_attribute(self, key, value):
        self.attributes[key] = value


def _build_app(*, authenticated_user=None):
    app = FastAPI()
    app.add_middleware(ObservabilityContextMiddleware)

    # Added after ObservabilityContextMiddleware -> outermost -> runs first,
    # so request.state.user is populated before dispatch() reads it.
    @app.middleware("http")
    async def _inject_user(request, call_next):
        if authenticated_user is not None:
            request.state.user = authenticated_user
        return await call_next(request)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def _patched_client(monkeypatch, fake_span: _FakeSpan, **build_kwargs) -> TestClient:
    monkeypatch.setattr(
        observability_context_module.trace, "get_current_span", lambda: fake_span
    )
    return TestClient(_build_app(**build_kwargs))


def test_sets_endpoint_method_and_status_code(monkeypatch):
    fake_span = _FakeSpan()
    client = _patched_client(monkeypatch, fake_span)

    response = client.get("/ping")

    assert response.status_code == 200
    assert fake_span.attributes["endpoint"] == "/ping"
    assert fake_span.attributes["method"] == "GET"
    assert fake_span.attributes["status_code"] == 200


def test_no_user_attributes_when_unauthenticated(monkeypatch):
    fake_span = _FakeSpan()
    client = _patched_client(monkeypatch, fake_span)

    client.get("/ping")

    assert "enduser.id" not in fake_span.attributes


def test_sets_user_attributes_when_authenticated(monkeypatch):
    fake_span = _FakeSpan()
    user = SimpleNamespace(id=42, email="alice@example.com", username="alice")
    client = _patched_client(monkeypatch, fake_span, authenticated_user=user)

    client.get("/ping")

    assert fake_span.attributes["enduser.id"] == "42"
    assert fake_span.attributes["enduser.email"] == "alice@example.com"
    assert fake_span.attributes["enduser.username"] == "alice"


def test_query_params_with_default_denylist_terms_are_scrubbed(monkeypatch):
    """Sensitive query params (matched via specula_client's DEFAULT_DENYLIST,
    e.g. the "password" substring) must never reach the observability backend
    in clear text."""
    fake_span = _FakeSpan()
    client = _patched_client(monkeypatch, fake_span)

    client.get("/ping?current_password=hunter2&topic=Heapsort")

    assert "hunter2" not in fake_span.attributes["http.query_params"]
    assert "REDACTED" in fake_span.attributes["http.query_params"]
    assert "Heapsort" in fake_span.attributes["http.query_params"]


def test_extra_pii_denylist_is_passed_to_scrub_pii(monkeypatch):
    """Verifies the wiring itself (EXTRA_PII_DENYLIST -> scrub_pii), decoupled
    from specula_client's DEFAULT_DENYLIST/matching semantics: the three
    extra terms today are substring-covered by DEFAULT_DENYLIST's "password"
    already (see config/observability.py's EXTRA_PII_DENYLIST docstring), so
    a behavioural test alone (as above) can't tell "the extension is wired
    in" apart from "the default denylist happened to catch it anyway". This
    test would fail if a future refactor silently dropped
    extra_denylist=EXTRA_PII_DENYLIST from the scrub_pii() call."""
    captured = {}

    def _fake_scrub_pii(value, *, extra_denylist=()):
        captured["extra_denylist"] = list(extra_denylist)
        return value

    monkeypatch.setattr(observability_context_module, "scrub_pii", _fake_scrub_pii)
    fake_span = _FakeSpan()
    client = _patched_client(monkeypatch, fake_span)

    client.get("/ping?topic=Heapsort")

    assert captured["extra_denylist"] == EXTRA_PII_DENYLIST


def test_query_params_omitted_when_scrubbing_fails(monkeypatch):
    """scrub_pii() fails closed (raises) on e.g. an unsupported value type or
    a circular reference; the middleware must drop http.query_params rather
    than falling back to the unscrubbed original, and must not break the
    request itself."""

    def _raising_scrub_pii(*args, **kwargs):
        raise TypeError("boom")

    monkeypatch.setattr(observability_context_module, "scrub_pii", _raising_scrub_pii)
    fake_span = _FakeSpan()
    client = _patched_client(monkeypatch, fake_span)

    response = client.get("/ping?topic=Heapsort")

    assert response.status_code == 200
    assert "http.query_params" not in fake_span.attributes
    # Rest of the context is unaffected by the scrubbing failure.
    assert fake_span.attributes["endpoint"] == "/ping"
