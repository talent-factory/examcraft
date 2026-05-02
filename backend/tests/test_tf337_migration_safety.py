"""Lightweight safety-checks for the tf337 audit_logs index migration.

Mirrors the pattern from ``test_tf333_migration_safety.py`` — a full
alembic upgrade/downgrade round-trip needs its own harness pointed at
a throwaway DB and is out of scope for the regular test suite. This
file pins the static contract (file present, correct revision chain,
expected index DDL) and the runtime behaviour (upgrade emits CREATE
INDEX, downgrade emits DROP INDEX) via a mocked ``op``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "2026_05_01_tf337_audit_logs_user_created_idx.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_tf337_migration_under_test", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_file_exists() -> None:
    assert MIGRATION_PATH.is_file(), f"migration not found at {MIGRATION_PATH}"


def test_revision_chain_is_intact() -> None:
    """Revision/down_revision wiring — a renamed predecessor would
    silently break the upgrade chain. Pin both ends."""
    module = _load_module()
    assert module.revision == "tf337_audit_logs_idx"
    assert module.down_revision == "tf336_llm_model"


def test_upgrade_creates_expected_index(monkeypatch) -> None:
    """Upgrade must execute a CREATE INDEX with the expected name and
    column order. The leading column must be ``user_id`` (every query
    filters on it) and the trailing column ``created_at DESC`` so PG
    can walk the index in ORDER BY order without a sort."""
    module = _load_module()
    fake_op = MagicMock()
    monkeypatch.setattr(module, "op", fake_op)

    module.upgrade()

    fake_op.execute.assert_called_once()
    sql = fake_op.execute.call_args[0][0]
    assert "CREATE INDEX IF NOT EXISTS" in sql
    assert module.INDEX_NAME in sql
    assert "ix_audit_logs_user_id_created_at_desc" == module.INDEX_NAME
    assert "audit_logs (user_id, created_at DESC)" in sql


def test_downgrade_drops_expected_index(monkeypatch) -> None:
    """Downgrade must drop the same index, idempotently."""
    module = _load_module()
    fake_op = MagicMock()
    monkeypatch.setattr(module, "op", fake_op)

    module.downgrade()

    fake_op.execute.assert_called_once()
    sql = fake_op.execute.call_args[0][0]
    assert "DROP INDEX IF EXISTS" in sql
    assert module.INDEX_NAME in sql


def test_upgrade_is_idempotent_via_if_not_exists() -> None:
    """The migration runs under AUTO_MIGRATE=true at every container
    start; without IF NOT EXISTS a re-run after a CI hiccup would
    crash the boot. Pin the guard at the source-text level."""
    text = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "IF NOT EXISTS" in text


def test_downgrade_is_idempotent_via_if_exists() -> None:
    """Symmetrical: a downgrade re-run must not hard-fail."""
    text = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "DROP INDEX IF EXISTS" in text
