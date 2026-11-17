"""``/api/v1/health`` meldet den Zitadel-Löschkonfigurations-Status (EXAMCRAFT-134)."""

import asyncio

import pytest

import main


def _health(monkeypatch, env, zitadel):
    calls = []

    def fake(use_cache=False):
        calls.append(use_cache)
        return zitadel

    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.setattr(
        "services.zitadel_user_service.check_zitadel_user_delete_config", fake
    )
    return asyncio.run(main.api_health_check()), calls


@pytest.mark.parametrize("zitadel", ["not_configured", "auth_rejected", "error"])
def test_production_degrades_on_broken_zitadel_config(monkeypatch, zitadel):
    result, _ = _health(monkeypatch, "production", zitadel)

    assert result["services"]["zitadel_user_delete"] == zitadel
    assert result["status"] == "degraded"


def test_unreachable_idp_stays_neutral_in_production(monkeypatch):
    ok, _ = _health(monkeypatch, "production", "ok")
    unreachable, _ = _health(monkeypatch, "production", "unreachable")

    assert unreachable["services"]["zitadel_user_delete"] == "unreachable"
    assert unreachable["status"] == ok["status"]


def test_zitadel_alone_does_not_degrade_outside_production(monkeypatch):
    ok, _ = _health(monkeypatch, "development", "ok")
    broken, _ = _health(monkeypatch, "development", "not_configured")

    assert broken["services"]["zitadel_user_delete"] == "not_configured"
    assert broken["status"] == ok["status"]


def test_endpoint_uses_the_cache(monkeypatch):
    _, calls = _health(monkeypatch, "production", "ok")

    assert calls == [True]
