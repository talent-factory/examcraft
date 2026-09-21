"""Tests for the Celery -> observability wiring (TF-359, TF-865).

Covers the moving parts that made the Celery worker blind to errors, now on
top of specula-client-python/OTel instead of sentry_sdk:
1. init_worker_observability() wires Celery instrumentation; init_observability()
   (API process) does not.
2. Both stay a no-op unless OTEL_EXPORTER_ENDPOINT AND SPECULA_TEAM_API_KEY are set
   (the original silent gap this replaced: SENTRY_DSN alone left Sentry inert).
3. The celeryd_init signal actually invokes init_worker_observability() in the worker.
4. The SuperAdmin worker-error trigger dispatches a failing task and is gated.
"""

import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import config.observability as observability
from main import app
from utils.auth_utils import get_current_superuser, get_current_user

_FAKE_ENDPOINT = "https://otel-collector.example.com"
_FAKE_TEAM_API_KEY = "fake-team-api-key"  # pragma: allowlist secret


class _FakeSpan:
    """Records set_attribute()/record_exception() calls, mirroring the
    _FakeSpan in test_observability_context_middleware.py."""

    def __init__(self):
        self.attributes: dict[str, object] = {}
        self.recorded_exceptions: list[Exception] = []

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def record_exception(self, exc):
        self.recorded_exceptions.append(exc)


@pytest.fixture(scope="module", autouse=True)
def _app_routers_registered():
    """Enter the app lifespan once so the admin routers exist.

    /api/admin/sentry-test/worker-error is registered during startup, not at
    import time. Without this the three endpoint tests below only pass when
    some earlier test file happened to trigger a lifespan first — they 404 in
    any run order that puts this file early (TF-660).
    """
    with TestClient(app):
        pass


# ---------------------------------------------------------------------------
# config/observability.py — instrumentation wiring + enable guard
# ---------------------------------------------------------------------------


def test_init_worker_observability_enables_celery_instrumentation(monkeypatch):
    """init_worker_observability() must wire Celery instrumentation so worker
    tasks are captured; init_observability() (API process) must not."""
    captured = {}
    monkeypatch.setattr(
        observability, "init_tracing", lambda **kwargs: captured.update(kwargs)
    )
    monkeypatch.setattr(observability, "_attach_log_handler", lambda *a, **k: None)
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)
    monkeypatch.setenv("ENVIRONMENT", "production")

    observability.init_worker_observability()

    assert captured["instrument_celery"] is True
    assert captured["service_name"] == observability.SERVICE_NAME_WORKER


def test_init_observability_does_not_enable_celery_instrumentation(monkeypatch):
    """The API-process init must not instrument Celery — that would double
    up with the worker's own instrumentation had it shared a process."""
    captured = {}
    monkeypatch.setattr(
        observability, "init_tracing", lambda **kwargs: captured.update(kwargs)
    )
    monkeypatch.setattr(observability, "_attach_log_handler", lambda *a, **k: None)
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)
    monkeypatch.setenv("ENVIRONMENT", "production")

    observability.init_observability()

    assert captured["instrument_celery"] is False
    assert captured["service_name"] == observability.SERVICE_NAME_API


def test_init_observability_noop_without_specula_team_api_key(monkeypatch):
    """Without SPECULA_TEAM_API_KEY, tracing must not initialize — this was
    the original bug: OTEL_EXPORTER_ENDPOINT (nee SENTRY_DSN) alone left
    observability inert on both API and worker."""
    calls = {"n": 0}
    monkeypatch.setattr(
        observability,
        "init_tracing",
        lambda **kwargs: calls.__setitem__("n", calls["n"] + 1),
    )
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)

    observability.init_observability()

    assert calls["n"] == 0


def test_init_observability_noop_without_otel_exporter_endpoint(monkeypatch):
    """Enable-guard other half: a team key alone must still be a no-op, so a
    misconfigured deploy never calls init_tracing() with a None endpoint."""
    calls = {"n": 0}
    monkeypatch.setattr(
        observability,
        "init_tracing",
        lambda **kwargs: calls.__setitem__("n", calls["n"] + 1),
    )
    monkeypatch.delenv("OTEL_EXPORTER_ENDPOINT", raising=False)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)

    observability.init_observability()

    assert calls["n"] == 0


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_disabled_state_logs_warning_in_staging_and_production(
    monkeypatch, caplog, environment
):
    """TF-359: a misconfigured staging/production deploy must be loud
    (WARNING), not an easily-missed INFO line -- the root logger sits at
    WARNING under uvicorn/celery, so INFO would be invisible there."""
    monkeypatch.delenv("OTEL_EXPORTER_ENDPOINT", raising=False)
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", environment)

    with caplog.at_level(logging.INFO):
        observability.init_observability()

    matching = [r for r in caplog.records if "[Observability] Disabled" in r.message]
    assert len(matching) == 1
    assert matching[0].levelno == logging.WARNING


@pytest.mark.parametrize("environment", ["development", "test"])
def test_disabled_state_logs_info_outside_staging_and_production(
    monkeypatch, caplog, environment
):
    """The same disabled state is only INFO in dev/test -- not a
    misconfiguration there, so it must not be loud."""
    monkeypatch.delenv("OTEL_EXPORTER_ENDPOINT", raising=False)
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", environment)

    with caplog.at_level(logging.INFO):
        observability.init_observability()

    matching = [r for r in caplog.records if "[Observability] Disabled" in r.message]
    assert len(matching) == 1
    assert matching[0].levelno == logging.INFO


@pytest.mark.parametrize(
    "environment,expected_sample_rate",
    [("development", 1.0), ("staging", 0.1), ("production", 0.1)],
)
def test_init_tracing_sample_rate_by_environment(
    monkeypatch, environment, expected_sample_rate
):
    """100% sampling in development, 10% everywhere else (including the
    previously-untested staging branch)."""
    captured = {}
    monkeypatch.setattr(
        observability, "init_tracing", lambda **kwargs: captured.update(kwargs)
    )
    monkeypatch.setattr(observability, "_attach_log_handler", lambda *a, **k: None)
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)
    monkeypatch.setenv("ENVIRONMENT", environment)

    observability.init_observability()

    assert captured["sample_rate"] == expected_sample_rate


def test_init_observability_survives_init_tracing_raising(monkeypatch, caplog):
    """Call-fail-open: an exception from specula_client.init_tracing() (bad
    endpoint, DNS failure, ...) must not prevent the process from finishing
    startup -- it degrades to "observability disabled" with a loud log."""

    def _boom(**kwargs):
        raise RuntimeError("collector unreachable")

    monkeypatch.setattr(observability, "init_tracing", _boom)
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)
    monkeypatch.setenv("ENVIRONMENT", "production")

    with caplog.at_level(logging.CRITICAL):
        observability.init_observability()  # must not raise

    assert any(
        "Failed to initialize" in r.message and r.levelno == logging.CRITICAL
        for r in caplog.records
    )


def test_attach_log_handler_registers_speculaloghandler_at_error_level(monkeypatch):
    """Exercises _attach_log_handler() for real (not monkeypatched away, see
    the other tests in this module) -- the ERROR-level filter is the only
    thing standing in for the retired sentry_sdk breadcrumb/event split; a
    regression to e.g. INFO would silently flood the collector."""
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)
    root_logger = logging.getLogger()
    handlers_before = list(root_logger.handlers)
    try:
        observability._attach_log_handler(
            observability.SERVICE_NAME_API, "production", "1.0.0"
        )
        new_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, observability.SpeculaLogHandler)
        ]
        assert len(new_handlers) == 1
        assert new_handlers[0].level == logging.ERROR

        # Calling it again must not duplicate the handler (dedup guard).
        observability._attach_log_handler(
            observability.SERVICE_NAME_API, "production", "1.0.0"
        )
        assert (
            len(
                [
                    h
                    for h in root_logger.handlers
                    if isinstance(h, observability.SpeculaLogHandler)
                ]
            )
            == 1
        )
    finally:
        root_logger.handlers = handlers_before


def test_instrument_app_skips_instrumentation_when_disabled(monkeypatch):
    """instrument_app() must not even attempt instrument_fastapi_app() when
    unconfigured, rather than relying solely on that call's own no-op
    contract (see the module docstring)."""
    calls = {"n": 0}
    monkeypatch.setattr(
        observability,
        "instrument_fastapi_app",
        lambda *a, **k: calls.__setitem__("n", calls["n"] + 1),
    )
    monkeypatch.delenv("OTEL_EXPORTER_ENDPOINT", raising=False)
    monkeypatch.delenv("SPECULA_TEAM_API_KEY", raising=False)

    observability.instrument_app(app)

    assert calls["n"] == 0


def test_instrument_app_instruments_when_configured(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        observability,
        "instrument_fastapi_app",
        lambda app_arg, **kwargs: captured.update(app=app_arg, **kwargs),
    )
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)

    observability.instrument_app(app)

    assert captured["app"] is app
    assert captured["otel_exporter_endpoint"] == _FAKE_ENDPOINT
    assert captured["specula_team_api_key"] == _FAKE_TEAM_API_KEY


def test_instrument_app_survives_instrument_fastapi_app_raising(monkeypatch, caplog):
    def _boom(*a, **k):
        raise RuntimeError("instrumentation failed")

    monkeypatch.setattr(observability, "instrument_fastapi_app", _boom)
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)

    with caplog.at_level(logging.CRITICAL):
        observability.instrument_app(app)  # must not raise

    assert any(r.levelno == logging.CRITICAL for r in caplog.records)


def test_disabled_when_specula_client_unavailable_even_if_configured(
    monkeypatch, caplog
):
    """Package-fail-open (TF-865, core/ must never hard-depend on proprietary
    code, see module docstring): a public/OSS build without specula_client
    installed must stay disabled -- at INFO, not WARNING, since that's an
    expected state rather than a misconfiguration -- even if
    OTEL_EXPORTER_ENDPOINT/SPECULA_TEAM_API_KEY are (irrelevantly) set."""
    monkeypatch.setattr(observability, "SPECULA_CLIENT_AVAILABLE", False)
    monkeypatch.setenv("OTEL_EXPORTER_ENDPOINT", _FAKE_ENDPOINT)
    monkeypatch.setenv("SPECULA_TEAM_API_KEY", _FAKE_TEAM_API_KEY)
    monkeypatch.setenv("ENVIRONMENT", "production")
    init_tracing_calls = {"n": 0}
    monkeypatch.setattr(
        observability,
        "init_tracing",
        lambda **kwargs: init_tracing_calls.__setitem__(
            "n", init_tracing_calls["n"] + 1
        ),
    )

    with caplog.at_level(logging.INFO):
        observability.init_observability()

    assert init_tracing_calls["n"] == 0
    matching = [r for r in caplog.records if "[Observability] Disabled" in r.message]
    assert len(matching) == 1
    assert matching[0].levelno == logging.INFO


def test_record_exception_noop_when_specula_client_unavailable(monkeypatch):
    """record_exception() must still record the exception itself on the span
    (raw OTel API, no specula_client needed for that) but skip
    tags/extra_context entirely -- there is no scrub_pii() to run them
    through and no exporter for them to reach anyway."""
    monkeypatch.setattr(observability, "SPECULA_CLIENT_AVAILABLE", False)
    fake_span = _FakeSpan()
    monkeypatch.setattr(observability.trace, "get_current_span", lambda: fake_span)
    exc = ValueError("boom")

    observability.record_exception(exc, tags={"user_id": 7})  # must not raise

    assert fake_span.recorded_exceptions == [exc]
    assert "user_id" not in fake_span.attributes


# ---------------------------------------------------------------------------
# config/observability.py — set_span_tag()/record_exception() (no mocking of
# the functions under test themselves, only of the OTel span they write to)
# ---------------------------------------------------------------------------


def test_set_span_tag_sets_stringified_attribute(monkeypatch):
    fake_span = _FakeSpan()
    monkeypatch.setattr(observability.trace, "get_current_span", lambda: fake_span)

    observability.set_span_tag("user_id", 42)

    assert fake_span.attributes["user_id"] == "42"


def test_set_span_tag_falls_back_when_str_raises(monkeypatch):
    class _Unstringifiable:
        def __str__(self):
            raise RuntimeError("nope")

    fake_span = _FakeSpan()
    monkeypatch.setattr(observability.trace, "get_current_span", lambda: fake_span)

    observability.set_span_tag("bad", _Unstringifiable())  # must not raise

    assert fake_span.attributes["bad"] == "<unrepresentable value>"


def test_record_exception_records_and_tags_span(monkeypatch):
    fake_span = _FakeSpan()
    monkeypatch.setattr(observability.trace, "get_current_span", lambda: fake_span)
    exc = ValueError("boom")

    observability.record_exception(
        exc, tags={"user_id": 7}, extra_context={"topic": "Heapsort"}
    )

    assert fake_span.recorded_exceptions == [exc]
    assert fake_span.attributes["user_id"] == "7"
    assert fake_span.attributes["extra.topic"] == "Heapsort"


def test_record_exception_scrubs_sensitive_tags(monkeypatch):
    """Unlike the retired global EventScrubber, record_exception() is the
    only line of defence against a caller passing a sensitive field through
    tags/extra_context -- it must scrub, not just stringify."""
    fake_span = _FakeSpan()
    monkeypatch.setattr(observability.trace, "get_current_span", lambda: fake_span)

    observability.record_exception(
        ValueError("boom"),
        tags={"admin_password": "hunter2", "user_id": 7},
        extra_context={"api_key": "sk-secret"},
    )

    assert fake_span.attributes["admin_password"] == "[REDACTED]"
    assert fake_span.attributes["user_id"] == "7"
    assert fake_span.attributes["extra.api_key"] == "[REDACTED]"


def test_record_exception_omits_tags_when_scrubbing_fails(monkeypatch):
    fake_span = _FakeSpan()
    monkeypatch.setattr(observability.trace, "get_current_span", lambda: fake_span)

    def _raising_scrub_pii(*args, **kwargs):
        raise TypeError("unsupported type")

    monkeypatch.setattr(observability, "scrub_pii", _raising_scrub_pii)
    exc = ValueError("boom")

    observability.record_exception(exc, tags={"user_id": 7})  # must not raise

    # The exception itself is still recorded -- only the (unscrubbable) tags
    # are dropped.
    assert fake_span.recorded_exceptions == [exc]
    assert "user_id" not in fake_span.attributes


# ---------------------------------------------------------------------------
# celery_app.py — fork-safe worker init via celeryd_init
# ---------------------------------------------------------------------------


def test_celeryd_init_signal_invokes_init_worker_observability(monkeypatch):
    """The worker must initialize observability on boot; main.py never runs there."""
    import celery_app  # noqa: F401  (import registers the celeryd_init receiver)
    import config.observability as observability_cfg
    from celery.signals import celeryd_init

    calls = {"n": 0}
    monkeypatch.setattr(
        observability_cfg,
        "init_worker_observability",
        lambda: calls.__setitem__("n", calls["n"] + 1),
    )

    celeryd_init.send(sender="test-worker")

    assert calls["n"] >= 1


# ---------------------------------------------------------------------------
# tasks/diagnostics_tasks.py — deliberate worker failure with task context
# ---------------------------------------------------------------------------


def test_trigger_test_error_raises_with_task_context(monkeypatch):
    """The diagnostic task must raise and tag user_id/topic so the verification
    event exercises the same triage path as a real worker failure."""
    from tasks.diagnostics_tasks import SentryPipelineTestError, trigger_test_error

    tags: dict[str, str] = {}
    monkeypatch.setattr(
        "tasks.diagnostics_tasks.set_span_tag",
        lambda k, v: tags.__setitem__(k, v),
    )

    with pytest.raises(SentryPipelineTestError):
        trigger_test_error.apply(kwargs={"user_id": 42}, throw=True)

    assert tags["user_id"] == "42"
    assert tags["topic"] == "sentry-pipeline-test"
    assert tags["diagnostic"] == "true"


# ---------------------------------------------------------------------------
# api/sentry_test.py — SuperAdmin worker-error endpoint (prod-safe)
# ---------------------------------------------------------------------------


def test_worker_error_endpoint_dispatches_for_superadmin(monkeypatch):
    """SuperAdmin can trigger the worker error; the task is dispatched onto a
    consumed queue and the Celery task id is returned for correlation."""
    import celery_app as celery_module

    sent = {}

    def _fake_send_task(name, **kwargs):
        sent["name"] = name
        sent["queue"] = kwargs.get("queue")
        sent["kwargs"] = kwargs.get("kwargs")
        return SimpleNamespace(id="fake-task-id")

    monkeypatch.setattr(celery_module.celery_app, "send_task", _fake_send_task)
    app.dependency_overrides[get_current_superuser] = lambda: SimpleNamespace(
        id=7, is_superuser=True
    )

    client = TestClient(app, raise_server_exceptions=True)
    resp = client.post("/api/admin/sentry-test/worker-error")

    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == "fake-task-id"
    assert sent["name"] == "tasks.diagnostics_tasks.trigger_test_error"
    # Must target a queue the worker actually consumes, else it would never run.
    assert sent["queue"] == "question_generation"
    assert sent["kwargs"]["user_id"] == 7


def test_worker_error_endpoint_forbidden_for_non_superadmin(monkeypatch):
    """A normal authenticated user must be rejected with 403 — the real
    get_current_superuser guard runs because only get_current_user is faked."""
    import celery_app as celery_module

    def _boom(*args, **kwargs):  # pragma: no cover - must never be reached
        raise AssertionError("send_task must not run for a non-superadmin")

    monkeypatch.setattr(celery_module.celery_app, "send_task", _boom)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=11, is_superuser=False
    )

    client = TestClient(app, raise_server_exceptions=True)
    resp = client.post("/api/admin/sentry-test/worker-error")

    assert resp.status_code == 403


def test_worker_error_endpoint_returns_503_when_broker_unreachable(monkeypatch):
    """If dispatch fails (broker down), the SuperAdmin must get an actionable
    503 — not an opaque 500 — so a degraded broker is distinguishable from a
    broken observability pipeline (mirrors the production dispatch path)."""
    import celery_app as celery_module

    def _broker_down(*args, **kwargs):
        raise ConnectionError("broker unreachable")

    monkeypatch.setattr(celery_module.celery_app, "send_task", _broker_down)
    app.dependency_overrides[get_current_superuser] = lambda: SimpleNamespace(
        id=7, is_superuser=True
    )

    client = TestClient(app, raise_server_exceptions=True)
    resp = client.post("/api/admin/sentry-test/worker-error")

    assert resp.status_code == 503
