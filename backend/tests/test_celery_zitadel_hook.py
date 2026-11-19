"""Worker-Boot-Prüfung der Zitadel-Löschkonfiguration (EXAMCRAFT-134)."""

import pytest
from celery.signals import celeryd_init

import celery_app


@pytest.fixture
def check(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "services.zitadel_user_service.check_zitadel_user_delete_config",
        lambda: calls.append(1) or "ok",
    )
    return calls


def test_hook_is_connected_to_celeryd_init():
    receivers = [r() for _, r in celeryd_init.receivers]
    assert celery_app._check_zitadel_user_delete_config in receivers


def test_hook_skips_outside_production(monkeypatch, check):
    monkeypatch.setenv("ENVIRONMENT", "development")
    celery_app._check_zitadel_user_delete_config()
    assert check == []


def test_hook_checks_once_in_production(monkeypatch, check):
    monkeypatch.setenv("ENVIRONMENT", "production")
    celery_app._check_zitadel_user_delete_config()
    assert check == [1]


def test_hook_never_blocks_worker_start(monkeypatch):
    def boom():
        raise RuntimeError("x")

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(
        "services.zitadel_user_service.check_zitadel_user_delete_config", boom
    )
    celery_app._check_zitadel_user_delete_config()  # wirft nicht
