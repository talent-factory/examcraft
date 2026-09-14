"""Tests für services.redis_service — neuer Ops-Alert-Client (TF-788)."""

from services.redis_service import (
    REDIS_DB_OPS_ALERTS,
    REDIS_DB_SESSIONS,
    RedisService,
)


def test_ops_alert_db_shares_sessions_db():
    """TF-815: Prod-Redis (Upstash) lehnt ``SELECT`` auf jeden Nicht-0-Index
    ab ("Only 0th database is supported!") — ein erster Fix-Versuch auf DB 3
    (geteilt mit MCP-OAuth) scheiterte live mit demselben Fehler ("Selected
    DB: 3"), was zeigt: diese Instanz unterstützt wirklich nur DB 0. Ops-Alerts
    teilen sich deshalb DB 0 mit Sessions statt irgendeinen anderen Index;
    Key-Präfixe (``oauth_state:*``/``avatar:*`` vs. ``ops_alert:state:*``)
    halten die Keyspaces getrennt."""
    assert REDIS_DB_OPS_ALERTS == REDIS_DB_SESSIONS


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
