"""Tests für Celery-Konfiguration"""


def test_celery_result_backend_uses_db3():
    """Celery Result Backend muss Redis DB 3 verwenden (DB 1 = Token-Blacklist)"""
    from celery_app import celery_app

    backend = celery_app.conf.result_backend
    assert backend is not None
    assert "/3" in backend, (
        f"Celery result backend muss DB 3 verwenden, aktuell: {backend}"
    )
