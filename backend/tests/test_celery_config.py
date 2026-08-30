"""Tests fuer Celery-Konfiguration"""


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
