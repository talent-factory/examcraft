"""Tests for the Celery -> Sentry observability wiring (TF-359).

Covers the four moving parts that made the Celery worker blind to errors:
1. CeleryIntegration is registered when Sentry initializes.
2. init_sentry() stays a no-op without ENABLE_SENTRY (the original silent gap).
3. The celeryd_init signal actually invokes init_sentry() in the worker.
4. The SuperAdmin worker-error trigger dispatches a failing task and is gated.
"""

from types import SimpleNamespace

import pytest
import sentry_sdk
from fastapi.testclient import TestClient

from main import app
from utils.auth_utils import get_current_superuser, get_current_user

_FAKE_DSN = "https://public@o0.ingest.sentry.io/0"  # pragma: allowlist secret


# ---------------------------------------------------------------------------
# config/sentry.py — integration registration + enable guard
# ---------------------------------------------------------------------------


def test_init_sentry_registers_celery_integration(monkeypatch):
    """init_sentry() must wire CeleryIntegration so worker tasks are captured."""
    captured = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setenv("ENABLE_SENTRY", "true")
    monkeypatch.setenv("SENTRY_DSN", _FAKE_DSN)
    monkeypatch.setenv("ENVIRONMENT", "production")

    from config.sentry import init_sentry

    init_sentry()

    integration_names = {type(i).__name__ for i in captured["integrations"]}
    assert "CeleryIntegration" in integration_names


def test_init_sentry_noop_without_enable_flag(monkeypatch):
    """Without ENABLE_SENTRY the SDK must not initialize — this was the bug:
    SENTRY_DSN alone left Sentry inert on both API and worker."""
    calls = {"n": 0}
    monkeypatch.setattr(
        sentry_sdk, "init", lambda **kwargs: calls.__setitem__("n", calls["n"] + 1)
    )
    monkeypatch.delenv("ENABLE_SENTRY", raising=False)
    monkeypatch.setenv("SENTRY_DSN", _FAKE_DSN)

    from config.sentry import init_sentry

    init_sentry()

    assert calls["n"] == 0


# ---------------------------------------------------------------------------
# celery_app.py — fork-safe worker init via celeryd_init
# ---------------------------------------------------------------------------


def test_celeryd_init_signal_invokes_init_sentry(monkeypatch):
    """The worker must initialize Sentry on boot; main.py never runs there."""
    import celery_app  # noqa: F401  (import registers the celeryd_init receiver)
    import config.sentry as sentry_cfg
    from celery.signals import celeryd_init

    calls = {"n": 0}
    monkeypatch.setattr(
        sentry_cfg, "init_sentry", lambda: calls.__setitem__("n", calls["n"] + 1)
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
    monkeypatch.setattr(sentry_sdk, "set_tag", lambda k, v: tags.__setitem__(k, v))

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
    broken Sentry pipeline (mirrors the production dispatch path)."""
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


@pytest.mark.parametrize("environment", ["production", "staging", "test"])
def test_init_sentry_ignore_errors_has_no_none_entries(monkeypatch, environment):
    """TF-592 regression: `"OperationalError" if environment == "development"
    else None` used to leave a literal `None` in `ignore_errors` for every
    non-development environment. sentry_sdk's `Client._is_ignored_error()`
    calls `issubclass(error, ignored_error)` for any non-string entry — with
    `ignored_error=None` that raises `TypeError: issubclass() arg 2 must be a
    class, a tuple of classes, or a union` for EVERY exception Sentry tried to
    capture, masking the real error (e.g. an LLM-Gateway timeout) behind an
    unrelated TypeError. Every entry must be a string in every environment
    other than development."""
    captured = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setenv("ENABLE_SENTRY", "true")
    monkeypatch.setenv("SENTRY_DSN", _FAKE_DSN)
    monkeypatch.setenv("ENVIRONMENT", environment)

    from config.sentry import init_sentry

    init_sentry()

    ignore_errors = captured["ignore_errors"]
    assert None not in ignore_errors
    assert all(isinstance(entry, str) for entry in ignore_errors)


def test_init_sentry_ignore_errors_survives_real_sentry_matching(monkeypatch):
    """Exercises the exact sentry_sdk code path from the production traceback:
    `Client._is_ignored_error()` iterating `ignore_errors` and calling
    `issubclass(error, ignored_error)` on non-string entries. Before the fix
    this raised `TypeError: issubclass() arg 2 must be a class, a tuple of
    classes, or a union` for an unrelated exception (here: TimeoutError,
    standing in for the openai.APITimeoutError seen in prod) — proving the
    bug masked real errors rather than merely being a lint nit."""
    captured = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setenv("ENABLE_SENTRY", "true")
    monkeypatch.setenv("SENTRY_DSN", _FAKE_DSN)
    monkeypatch.setenv("ENVIRONMENT", "production")

    from config.sentry import init_sentry

    init_sentry()

    client = sentry_sdk.Client(dsn=_FAKE_DSN, ignore_errors=captured["ignore_errors"])
    try:
        raise TimeoutError("Request timed out.")
    except TimeoutError:
        import sys

        exc_info = sys.exc_info()

    # Must not raise TypeError, and a real (non-ignored) error must not be
    # swallowed either.
    assert client._is_ignored_error({}, {"exc_info": exc_info}) is False


def test_init_sentry_noop_when_dsn_missing(monkeypatch):
    """Enable-guard other half: flag on but no DSN must still be a no-op, so a
    misconfigured deploy never calls sentry_sdk.init with a None DSN."""
    calls = {"n": 0}
    monkeypatch.setattr(
        sentry_sdk, "init", lambda **kwargs: calls.__setitem__("n", calls["n"] + 1)
    )
    monkeypatch.setenv("ENABLE_SENTRY", "true")
    monkeypatch.delenv("SENTRY_DSN", raising=False)

    from config.sentry import init_sentry

    init_sentry()

    assert calls["n"] == 0
