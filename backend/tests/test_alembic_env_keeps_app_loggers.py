"""Regression guard: running Alembic in-process must not silence app loggers.

`database._run_migrations_or_create_all()` calls `command.stamp` (fresh
database) or `command.upgrade` (AUTO_MIGRATE=true) inside the running API
process. Both execute `alembic/env.py`, which applies `alembic.ini` via
`logging.config.fileConfig`. With the default `disable_existing_loggers=True`
that call disables every logger already created at that point — i.e. the
module loggers of all routers and services imported before startup. From then
on their warnings and errors vanish for the lifetime of the process.

Found via CI (TF-773 PR 2a): on the fresh CI database the first app startup
stamps head, after which `caplog` saw nothing from `api.v1.help`,
`api.org_units` or `api.v1.webhooks`.

The stamp runs in offline mode (`sql=True`), so no database is needed; env.py
is executed exactly as on startup.
"""

import io
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_alembic_env_does_not_disable_existing_loggers():
    probe = logging.getLogger("api.tf773_alembic_logger_probe")
    assert probe.disabled is False

    # env.py's fileConfig() reconfigures the *root* logger's handlers/level
    # as a side effect (that part is unavoidable, not what's being guarded
    # here) -- restore it afterwards so this test doesn't leak logging state
    # into whatever test runs next in the same process.
    root = logging.getLogger()
    root_handlers = list(root.handlers)
    root_level = root.level
    try:
        cfg = Config(str(_BACKEND_DIR / "alembic.ini"), output_buffer=io.StringIO())
        cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
        command.stamp(cfg, "head", sql=True)

        assert probe.disabled is False
    finally:
        root.handlers = root_handlers
        root.setLevel(root_level)
