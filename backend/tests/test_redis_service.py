"""Tests für services.redis_service — DB-Partitionierung (TF-788, TF-815, TF-816)."""

import pytest

from services.redis_service import (
    REDIS_DB_ACTIVITY,
    REDIS_DB_BLACKLIST,
    REDIS_DB_MCP_OAUTH,
    REDIS_DB_OPS_ALERTS,
    REDIS_DB_RATELIMIT,
    REDIS_DB_SESSIONS,
    RedisService,
)


@pytest.mark.parametrize(
    "db_constant",
    [
        REDIS_DB_OPS_ALERTS,
        REDIS_DB_BLACKLIST,
        REDIS_DB_RATELIMIT,
        REDIS_DB_MCP_OAUTH,
        REDIS_DB_ACTIVITY,
    ],
)
def test_non_session_dbs_share_sessions_db(db_constant):
    """TF-815/TF-816: Prod-Redis (Upstash) lehnt ``SELECT`` auf jeden
    Nicht-0-Index ab ("Only 0th database is supported!") — ein erster
    Fix-Versuch auf DB 3 (geteilt mit MCP-OAuth) scheiterte live mit demselben
    Fehler ("Selected DB: 3"), was zeigt: diese Instanz unterstützt wirklich
    nur DB 0. TF-816 hat denselben Befund für Blacklist/Ratelimit/MCP-OAuth
    bestätigt — alle vier teilen sich deshalb DB 0 mit Sessions statt eigene
    Indizes; disjunkte Key-Präfixe (``session:*``/``user_sessions:*``,
    ``blacklist:*``, ``ratelimit:*``, ``mcp:*``, ``ops_alert:state:*``)
    halten die Keyspaces getrennt."""
    assert db_constant == REDIS_DB_SESSIONS


@pytest.mark.parametrize(
    "getter_name,db_constant,attr_name",
    [
        ("get_session_client", REDIS_DB_SESSIONS, "_session_client"),
        ("get_blacklist_client", REDIS_DB_BLACKLIST, "_blacklist_client"),
        ("get_ratelimit_client", REDIS_DB_RATELIMIT, "_ratelimit_client"),
        ("get_mcp_oauth_client", REDIS_DB_MCP_OAUTH, "_mcp_oauth_client"),
        ("get_ops_alert_client", REDIS_DB_OPS_ALERTS, "_ops_alert_client"),
        ("get_activity_client", REDIS_DB_ACTIVITY, "_activity_client"),
    ],
)
def test_get_client_uses_correct_db_and_caches_instance(
    getter_name, db_constant, attr_name
):
    setattr(RedisService, attr_name, None)
    try:
        getter = getattr(RedisService, getter_name)
        client = getter()
        assert client.connection_pool.connection_kwargs["db"] == db_constant
        assert getter() is client  # Singleton
    finally:
        RedisService.close_all()


def test_close_all_clears_every_client():
    RedisService.get_session_client()
    RedisService.get_blacklist_client()
    RedisService.get_ratelimit_client()
    RedisService.get_mcp_oauth_client()
    RedisService.get_ops_alert_client()
    RedisService.get_activity_client()

    RedisService.close_all()

    assert RedisService._session_client is None
    assert RedisService._blacklist_client is None
    assert RedisService._ratelimit_client is None
    assert RedisService._mcp_oauth_client is None
    assert RedisService._ops_alert_client is None
    assert RedisService._activity_client is None
