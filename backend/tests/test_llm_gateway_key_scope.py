# core/backend/tests/test_llm_gateway_key_scope.py
"""TF-999: startup check that every alias ExamCraft uses is in the scope of
the configured gateway Virtual Key (analogous to the TF-438 startup
validation), so a missing alias shows up at deploy time instead of as a 403
on the first portfolio job."""

import importlib

import httpx
import pytest

import services.llm_gateway as gw


@pytest.fixture
def m(monkeypatch):
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gw:4000/v1")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "sk-test")
    return importlib.reload(gw)


def _transport(models=None, status_code=200, exc=None, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if exc is not None:
            raise exc
        return httpx.Response(status_code, json={"info": {"models": models}})

    return httpx.MockTransport(handler)


def test_required_aliases_cover_all_alias_constants(m):
    constants = {v for k, v in vars(m).items() if k.startswith("ALIAS_")}
    assert set(m.REQUIRED_ALIASES) == constants


def test_queries_key_info_without_v1_suffix_and_with_bearer_key(m):
    seen = []
    m.check_key_alias_scope(transport=_transport(list(m.REQUIRED_ALIASES), seen=seen))
    assert str(seen[0].url) == "http://gw:4000/key/info"
    assert seen[0].headers["Authorization"] == "Bearer sk-test"


def test_ok_when_all_aliases_in_scope(m):
    result = m.check_key_alias_scope(
        transport=_transport(list(m.REQUIRED_ALIASES) + ["tf/other"])
    )
    assert result == {"status": "ok", "missing_aliases": []}


def test_reports_missing_portfolio_aliases(m):
    scope = [
        a
        for a in m.REQUIRED_ALIASES
        if a not in (m.ALIAS_PORTFOLIO_CLASSIFICATION, m.ALIAS_PORTFOLIO_GRADING)
    ]
    result = m.check_key_alias_scope(transport=_transport(scope))
    assert result == {
        "status": "missing_aliases",
        "missing_aliases": [
            m.ALIAS_PORTFOLIO_CLASSIFICATION,
            m.ALIAS_PORTFOLIO_GRADING,
        ],
    }


@pytest.mark.parametrize("models", [[], None, ["all-proxy-models"]])
def test_unrestricted_key_counts_as_ok(m, models):
    """LiteLLM: an empty model list (or all-proxy-models) means no restriction."""
    result = m.check_key_alias_scope(transport=_transport(models))
    assert result["status"] == "ok"


def test_unreachable_gateway_is_fail_open(m):
    result = m.check_key_alias_scope(
        transport=_transport(exc=httpx.ConnectError("connection refused"))
    )
    assert result == {"status": "unreachable", "missing_aliases": []}


def test_gateway_5xx_counts_as_unreachable(m):
    result = m.check_key_alias_scope(transport=_transport(status_code=503))
    assert result["status"] == "unreachable"


def test_rejected_key_is_reported_as_error(m):
    result = m.check_key_alias_scope(transport=_transport(status_code=401))
    assert result == {"status": "key_rejected", "missing_aliases": []}


def test_unparseable_response_does_not_raise(m):
    def handler(request):
        return httpx.Response(200, text="<html>")

    result = m.check_key_alias_scope(transport=httpx.MockTransport(handler))
    assert result["status"] == "unknown"


def test_not_configured_without_gateway(monkeypatch):
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    mod = importlib.reload(gw)
    assert mod.check_key_alias_scope()["status"] == "not_configured"


def test_not_configured_without_key(monkeypatch):
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gw:4000")
    monkeypatch.delenv("LLM_GATEWAY_API_KEY", raising=False)
    mod = importlib.reload(gw)
    assert mod.check_key_alias_scope()["status"] == "not_configured"


def test_last_result_is_pending_before_first_check(m):
    assert m.last_key_alias_scope() == {"status": "pending", "missing_aliases": []}


def test_log_key_alias_scope_logs_missing_aliases_as_error(m, monkeypatch):
    records = []
    monkeypatch.setattr(m.logger, "error", lambda msg, *a: records.append(msg % a))

    result = m.log_key_alias_scope(transport=_transport([m.ALIAS_GENERATION]))

    assert result["status"] == "missing_aliases"
    assert m.last_key_alias_scope() == result
    assert len(records) == 1
    assert m.ALIAS_PORTFOLIO_GRADING in records[0]
    assert "TF-999" in records[0]


def test_log_key_alias_scope_only_warns_when_unreachable(m, monkeypatch):
    errors, warnings = [], []
    monkeypatch.setattr(m.logger, "error", lambda msg, *a: errors.append(msg))
    monkeypatch.setattr(m.logger, "warning", lambda msg, *a: warnings.append(msg))

    m.log_key_alias_scope(transport=_transport(exc=httpx.ReadTimeout("timeout")))

    assert errors == []
    assert len(warnings) == 1
    assert m.last_key_alias_scope()["status"] == "unreachable"


def test_start_check_runs_in_background_without_blocking(m, monkeypatch):
    """A slow/unreachable gateway must not block app or worker startup."""
    import threading

    release = threading.Event()
    done = threading.Event()

    def slow_check(**_kwargs):
        release.wait(5)
        done.set()
        return {"status": "unreachable", "missing_aliases": []}

    monkeypatch.setattr(m, "log_key_alias_scope", slow_check)

    thread = m.start_key_alias_scope_check()

    assert thread.daemon is True
    assert not done.is_set()  # returned while the check is still running
    release.set()
    thread.join(5)
    assert done.is_set()


def test_celeryd_init_starts_key_scope_check(monkeypatch):
    import celery_app  # noqa: F401  (import registers the celeryd_init receivers)
    from celery.signals import celeryd_init

    from services import llm_gateway

    calls = []
    monkeypatch.setattr(
        llm_gateway, "start_key_alias_scope_check", lambda: calls.append(1)
    )

    celeryd_init.send(sender="test-worker")

    assert calls == [1]


def test_api_health_reports_key_scope_and_degrades_on_missing_aliases(monkeypatch):
    import asyncio

    import main
    from services import llm_gateway

    missing = {
        "status": "missing_aliases",
        "missing_aliases": [llm_gateway.ALIAS_PORTFOLIO_GRADING],
    }
    monkeypatch.setattr(llm_gateway, "last_key_alias_scope", lambda: missing)

    health = asyncio.run(main.api_health_check())

    assert health["services"]["llm_gateway_key_scope"] == missing
    assert health["status"] == "degraded"


def test_api_health_does_not_degrade_while_scope_unverified(monkeypatch):
    import asyncio

    import main
    from services import llm_gateway

    ok = {"status": "ok", "missing_aliases": []}
    monkeypatch.setattr(llm_gateway, "last_key_alias_scope", lambda: ok)
    baseline = asyncio.run(main.api_health_check())["status"]

    unreachable = {"status": "unreachable", "missing_aliases": []}
    monkeypatch.setattr(llm_gateway, "last_key_alias_scope", lambda: unreachable)
    health = asyncio.run(main.api_health_check())

    assert health["services"]["llm_gateway_key_scope"] == unreachable
    assert health["status"] == baseline
