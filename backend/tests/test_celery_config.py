"""Tests fuer Celery-Konfiguration"""


def test_celery_result_backend_uses_redis():
    """Celery Result Backend muss Redis verwenden (DB haengt von REDIS_URL / CELERY_RESULT_BACKEND ab)"""
    from celery_app import celery_app

    backend = celery_app.conf.result_backend
    assert backend is not None
    assert backend.startswith("redis://"), (
        f"Celery result backend muss Redis verwenden, aktuell: {backend}"
    )
