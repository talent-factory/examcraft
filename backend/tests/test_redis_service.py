"""Tests für services.redis_service — neuer Ops-Alert-Client (TF-788)."""

from services.redis_service import (
    REDIS_DB_MCP_OAUTH,
    REDIS_DB_OPS_ALERTS,
    RedisService,
)


def test_ops_alert_db_shares_mcp_oauth_db():
    """TF-815: Prod-Redis (Upstash) lehnt ``SELECT 4`` ab ("Only 0th database
    is supported! Selected DB: 4") — 0-3 sind die praktische Obergrenze.
    Ops-Alerts teilen sich deshalb DB 3 mit dem MCP-OAuth-Store statt einen
    eigenen Index zu bekommen; Key-Präfixe (``mcp:*`` vs. ``ops_alert:state:*``)
    halten die Keyspaces getrennt."""
    assert REDIS_DB_OPS_ALERTS == REDIS_DB_MCP_OAUTH


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
