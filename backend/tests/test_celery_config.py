"""Tests fuer Celery-Konfiguration"""

import builtins

import pytest


def test_celery_result_backend_uses_redis():
    """Celery Result Backend muss Redis verwenden (DB haengt von REDIS_URL / CELERY_RESULT_BACKEND ab)"""
    from celery_app import celery_app

    backend = celery_app.conf.result_backend
    assert backend is not None
    assert backend.startswith("redis://"), (
        f"Celery result backend muss Redis verwenden, aktuell: {backend}"
    )


def test_all_beat_scheduled_tasks_are_routed_to_a_consumed_queue():
    """Jeder Task in `beat_schedule` MUSS eine explizite `task_routes`-Route
    auf eine Queue haben, die auch in `task_queues` deklariert ist — sonst
    landet er still auf der nie konsumierten Default-Queue `celery` und
    läuft NIE (der no-`-Q`-Fly-Worker konsumiert nur `task_queues`, die
    docker-compose-Worker nur ihre `--queues=`-Liste).

    Genau dieser Bug traf TF-745 (`tasks.gdpr_tasks.process_scheduled_deletions`/
    `execute_gdpr_deletion`) und rückwirkend auch die drei älteren TF-329-
    Watchdogs (`tasks.maintenance_tasks.*`) — bis zu diesem Fix hatte KEINER
    der vier `beat_schedule`-Einträge eine Route. Mirrors
    `test_import_submissions_task.py::test_import_task_is_routed_to_a_consumed_queue`,
    aber generisch für alle Beat-Tasks statt nur einen — damit ein künftig
    neu ergänzter `beat_schedule`-Eintrag ohne Route automatisch auffällt,
    statt erst in Produktion als "läuft nie" bemerkt zu werden.
    """
    from celery_app import celery_app

    declared_queues = {q.name for q in (celery_app.conf.task_queues or ())}
    routes = celery_app.conf.task_routes or {}

    missing = []
    for entry in (celery_app.conf.beat_schedule or {}).values():
        task_name = entry["task"]
        route = routes.get(task_name)
        if route is None or route.get("queue") not in declared_queues:
            missing.append(task_name)

    assert not missing, (
        "Diese beat_schedule-Tasks haben keine Route auf eine tatsächlich "
        "konsumierte Queue und würden nie ausgeführt: " + ", ".join(sorted(missing))
    )


def test_premium_ops_alert_registration_empty_in_core_mode():
    from celery_app import _resolve_premium_ops_alert_registration

    beat, routes = _resolve_premium_ops_alert_registration("core")
    assert beat == {}
    assert routes == {}


def test_premium_ops_alert_registration_reflects_actual_importability_in_full_mode():
    """In 'full' mode, the resolver populates the beat/route entries ONLY if
    `premium.tasks.ops_alert_tasks` is actually importable in this test
    environment. Core's own CI job (test-core) runs core/backend/tests/ bare,
    with no premium import path set up — there the resolver must gracefully
    degrade to empty dicts (see its own docstring), matching the same
    fail-safe behavior a Core-only production deployment would see. The
    Docker-based full stack and premium's own CI job DO have premium
    importable, where this test asserts the populated case instead.
    """
    from celery_app import _resolve_premium_ops_alert_registration

    try:
        import premium.tasks.ops_alert_tasks  # noqa: F401

        premium_importable = True
    except ImportError:
        premium_importable = False

    beat, routes = _resolve_premium_ops_alert_registration("full")

    if not premium_importable:
        assert beat == {}
        assert routes == {}
        return

    task_name = "premium.tasks.ops_alert_tasks.check_ops_alert_thresholds"
    assert beat["check-ops-alert-thresholds"]["task"] == task_name
    assert routes[task_name] == {
        "queue": "maintenance_processing",
        "routing_key": "maintenance.process",
    }


def test_premium_ops_alert_registration_import_error_deterministically_degrades(
    monkeypatch,
):
    """Erzwingt den ImportError-Zweig unabhängig von der Testumgebung (statt
    sich wie test_..._reflects_actual_importability_in_full_mode auf
    Umgebungs-Zufall zu verlassen, ob premium importierbar ist) — deckt damit
    das ``except ImportError: logger.warning(...); return {}, {}``-Verhalten
    deterministisch ab."""
    from celery_app import _resolve_premium_ops_alert_registration

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "premium.tasks.ops_alert_tasks":
            raise ImportError("No module named 'premium.tasks.ops_alert_tasks'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    beat, routes = _resolve_premium_ops_alert_registration("full")

    assert beat == {}
    assert routes == {}


def test_premium_ops_alert_registration_non_import_error_degrades_gracefully(
    monkeypatch,
):
    """Ein Bug in premium.tasks.ops_alert_tasks (oder einem seiner Imports),
    der keine ImportError ist — z. B. ein AttributeError durch einen
    Tippfehler — darf nicht ungefangen aus dieser Funktion propagieren.
    Sonst würde er den Import von celery_app selbst crashen lassen, und
    damit (celery_app wird auch von main.py importiert) das gesamte
    FastAPI-Backend, nicht nur den Celery-Worker."""
    from celery_app import _resolve_premium_ops_alert_registration

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "premium.tasks.ops_alert_tasks":
            raise AttributeError("boom: simulierter Bug beim Import")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    beat, routes = _resolve_premium_ops_alert_registration("full")

    assert beat == {}
    assert routes == {}


def test_ops_alert_task_is_registered_and_routed_in_running_app():
    """Läuft die Suite im Full-Modus (docker-compose.full.yml setzt
    DEPLOYMENT_MODE=full, siehe CLAUDE.md), muss der echte, bereits
    konstruierte celery_app diesen Task kennen und routen — nicht nur die
    reine Resolver-Funktion oben."""
    from celery_app import celery_app

    task_name = "premium.tasks.ops_alert_tasks.check_ops_alert_thresholds"
    if task_name not in celery_app.conf.task_routes:
        pytest.skip("DEPLOYMENT_MODE != full in dieser Testumgebung")
    assert "check-ops-alert-thresholds" in celery_app.conf.beat_schedule


def test_premium_portfolio_ingestion_task_registration_empty_in_core_mode():
    from celery_app import _resolve_premium_portfolio_ingestion_task_registration

    routes = _resolve_premium_portfolio_ingestion_task_registration("core")
    assert routes == {}


def test_premium_portfolio_ingestion_task_registration_reflects_actual_importability_in_full_mode():
    """Mirrors
    ``test_premium_ops_alert_registration_reflects_actual_importability_in_full_mode``:
    in 'full' mode, the resolver populates the route entry ONLY if
    ``premium.tasks.portfolio_ingestion_tasks`` is actually importable in
    this test environment."""
    from celery_app import _resolve_premium_portfolio_ingestion_task_registration

    try:
        import premium.tasks.portfolio_ingestion_tasks  # noqa: F401

        premium_importable = True
    except ImportError:
        premium_importable = False

    routes = _resolve_premium_portfolio_ingestion_task_registration("full")

    if not premium_importable:
        assert routes == {}
        return

    task_name = "premium.tasks.portfolio_ingestion_tasks.run_portfolio_ingestion"
    assert routes[task_name] == {
        "queue": "document_processing",
        "routing_key": "document.process",
    }


def test_premium_portfolio_ingestion_task_registration_import_error_deterministically_degrades(
    monkeypatch,
):
    """Deterministic counterpart to the "reflects actual importability" test
    above — mirrors
    ``test_premium_ops_alert_registration_import_error_deterministically_degrades``."""
    from celery_app import _resolve_premium_portfolio_ingestion_task_registration

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "premium.tasks.portfolio_ingestion_tasks":
            raise ImportError(
                "No module named 'premium.tasks.portfolio_ingestion_tasks'"
            )
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    routes = _resolve_premium_portfolio_ingestion_task_registration("full")

    assert routes == {}


def test_premium_portfolio_ingestion_task_registration_non_import_error_degrades_gracefully(
    monkeypatch,
):
    """Mirrors
    ``test_premium_ops_alert_registration_non_import_error_degrades_gracefully``
    — a non-``ImportError`` bug on import must not propagate and crash
    ``celery_app`` (and with it ``main.py``, which also imports it)."""
    from celery_app import _resolve_premium_portfolio_ingestion_task_registration

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "premium.tasks.portfolio_ingestion_tasks":
            raise AttributeError("boom: simulierter Bug beim Import")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    routes = _resolve_premium_portfolio_ingestion_task_registration("full")

    assert routes == {}


def test_portfolio_ingestion_task_is_registered_and_routed_in_running_app():
    """Läuft die Suite im Full-Modus, muss der echte, bereits konstruierte
    celery_app diesen Task routen — nicht nur die reine Resolver-Funktion
    oben. Mirrors ``test_ops_alert_task_is_registered_and_routed_in_running_app``."""
    from celery_app import celery_app

    task_name = "premium.tasks.portfolio_ingestion_tasks.run_portfolio_ingestion"
    if task_name not in celery_app.conf.task_routes:
        pytest.skip("DEPLOYMENT_MODE != full in dieser Testumgebung")
    assert celery_app.conf.task_routes[task_name]["queue"] == "document_processing"


def test_premium_portfolio_watchdog_registration_empty_in_core_mode():
    from celery_app import _resolve_premium_portfolio_watchdog_registration

    beat, routes = _resolve_premium_portfolio_watchdog_registration("core")
    assert beat == {}
    assert routes == {}


def test_premium_portfolio_watchdog_registration_reflects_actual_importability_in_full_mode():
    """Mirrors
    ``test_premium_ops_alert_registration_reflects_actual_importability_in_full_mode``:
    in 'full' mode, the resolver populates the beat/route entries ONLY if
    ``premium.tasks.portfolio_watchdog_tasks`` is actually importable in
    this test environment."""
    from celery_app import _resolve_premium_portfolio_watchdog_registration

    try:
        import premium.tasks.portfolio_watchdog_tasks  # noqa: F401

        premium_importable = True
    except ImportError:
        premium_importable = False

    beat, routes = _resolve_premium_portfolio_watchdog_registration("full")

    if not premium_importable:
        assert beat == {}
        assert routes == {}
        return

    task_name = (
        "premium.tasks.portfolio_watchdog_tasks.reap_stuck_portfolio_ingestion_jobs"
    )
    assert (
        beat["reap-stuck-portfolio-ingestion-jobs-every-5-minutes"]["task"] == task_name
    )
    assert routes[task_name] == {
        "queue": "maintenance_processing",
        "routing_key": "maintenance.process",
    }


def test_premium_portfolio_watchdog_registration_import_error_deterministically_degrades(
    monkeypatch,
):
    """Mirrors
    ``test_premium_ops_alert_registration_import_error_deterministically_degrades``."""
    from celery_app import _resolve_premium_portfolio_watchdog_registration

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "premium.tasks.portfolio_watchdog_tasks":
            raise ImportError(
                "No module named 'premium.tasks.portfolio_watchdog_tasks'"
            )
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    beat, routes = _resolve_premium_portfolio_watchdog_registration("full")

    assert beat == {}
    assert routes == {}


def test_premium_portfolio_watchdog_registration_non_import_error_degrades_gracefully(
    monkeypatch,
):
    """Mirrors
    ``test_premium_ops_alert_registration_non_import_error_degrades_gracefully``
    — a non-``ImportError`` bug on import must not propagate and crash
    ``celery_app`` (and with it ``main.py``, which also imports it)."""
    from celery_app import _resolve_premium_portfolio_watchdog_registration

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "premium.tasks.portfolio_watchdog_tasks":
            raise AttributeError("boom: simulierter Bug beim Import")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    beat, routes = _resolve_premium_portfolio_watchdog_registration("full")

    assert beat == {}
    assert routes == {}


def test_portfolio_watchdog_task_is_registered_and_routed_in_running_app():
    """Läuft die Suite im Full-Modus, muss der echte, bereits konstruierte
    celery_app diesen Task routen — nicht nur die reine Resolver-Funktion
    oben. Mirrors ``test_ops_alert_task_is_registered_and_routed_in_running_app``."""
    from celery_app import celery_app

    task_name = (
        "premium.tasks.portfolio_watchdog_tasks.reap_stuck_portfolio_ingestion_jobs"
    )
    if task_name not in celery_app.conf.task_routes:
        pytest.skip("DEPLOYMENT_MODE != full in dieser Testumgebung")
    assert (
        "reap-stuck-portfolio-ingestion-jobs-every-5-minutes"
        in celery_app.conf.beat_schedule
    )
