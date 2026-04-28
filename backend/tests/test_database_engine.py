"""Tests für SQLAlchemy-Engine-Konfiguration in database.py.

Wir prüfen die drei Resilienz-Settings (`pool_recycle`, `connect_timeout`) und
die zwei Kapazitäts-Settings (`pool_size`, `max_overflow`) per Introspection
des Engine-Objekts. Hintergrund: TF-327 (SQLAlchemy Pool-Robustheit) — die
Werte adressieren konkret die DB-Hicks aus dem Demo-Vorfall am 2026-04-28.
"""


def test_engine_pool_recycle_is_30_minutes():
    """pool_recycle=1800 erzwingt periodische Re-Connects unter Fly-Routing-Idle-Timeout."""
    from database import engine

    assert engine.pool._recycle == 1800, (
        f"Expected pool_recycle=1800 (30 min) but got {engine.pool._recycle}. "
        "Lower than Fly internalrouting's typical ~5–10 min idle timeout would be "
        "wasteful; higher risks stale connections after long idle periods."
    )


def test_engine_pool_size_is_10():
    """pool_size=10 stellt Basis-Kapazität für concurrent FastAPI-Requests bereit."""
    from database import engine

    assert engine.pool.size() == 10, (
        f"Expected pool_size=10 but got {engine.pool.size()}. "
        "Default of 5 is too tight for our concurrent-request load."
    )


def test_engine_pool_max_overflow_is_20():
    """max_overflow=20 erlaubt 30 gleichzeitige Verbindungen unter Spitzenlast."""
    from database import engine

    assert engine.pool._max_overflow == 20, (
        f"Expected max_overflow=20 but got {engine.pool._max_overflow}. "
        "Combined with pool_size=10, gives 30 concurrent connections under burst."
    )


def test_engine_connect_args_have_connect_timeout_5_seconds():
    """connect_args={'connect_timeout': 5} kappt hängende DNS-/TCP-Verbindungsaufbauten.

    SQLAlchemy 2.x merges `connect_args` mit den URL-derived kwargs in `cparams`,
    das als zweites Closure-Element des Pool-Creators gespeichert wird — die rohen
    connect_args sind dort materialisiert und werden 1:1 an psycopg2 übergeben.
    """
    from database import engine

    # In SQLAlchemy 2.x the pool creator closure captures `cparams` (immutabledict)
    # which holds the merged connect_args + URL-derived connection kwargs. We
    # locate the cell BY NAME via co_freevars rather than by positional index —
    # survives any future closure reorder and fails loudly with ValueError if
    # the variable is ever renamed (so the test breaks visibly, not silently).
    creator = engine.pool._creator
    idx = creator.__code__.co_freevars.index("cparams")
    cparams = creator.__closure__[idx].cell_contents
    assert cparams.get("connect_timeout") == 5, (
        f"Expected connect_timeout=5 in pool creator cparams but got "
        f"{cparams.get('connect_timeout')!r}. The 5 s ceiling protects against "
        "hanging DNS lookups and stuck TCP handshakes during Fly routing flaps."
    )


def test_engine_pool_pre_ping_remains_enabled():
    """pool_pre_ping=True (already present pre-TF-327) must be preserved."""
    from database import engine

    # SQLAlchemy stores pool_pre_ping on the pool; the attribute is `_pre_ping`.
    assert engine.pool._pre_ping is True, (
        "pool_pre_ping was disabled — must stay True to validate connections "
        "at checkout (complementary to pool_recycle's preventive recycling)."
    )
