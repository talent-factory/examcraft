"""Tests für services.redis_service — neuer Ops-Alert-Client (TF-788)."""

from services.redis_service import REDIS_DB_OPS_ALERTS, RedisService


def test_ops_alert_db_index_is_4():
    assert REDIS_DB_OPS_ALERTS == 4


def test_get_ops_alert_client_uses_correct_db_and_caches_instance():
    RedisService._ops_alert_client = None
    try:
        client = RedisService.get_ops_alert_client()
        assert client.connection_pool.connection_kwargs["db"] == REDIS_DB_OPS_ALERTS
        assert RedisService.get_ops_alert_client() is client  # Singleton
    finally:
        RedisService.close_all()


def test_close_all_clears_ops_alert_client():
    RedisService.get_ops_alert_client()
    RedisService.close_all()
    assert RedisService._ops_alert_client is None
