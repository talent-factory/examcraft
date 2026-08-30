"""Lightweight safety-checks for the tf745 FK-ondelete-drift migration
(TF-745 PR review fix — the migration previously had no automated test at
all, despite fixing exactly the kind of silent FK-policy drift this repo
has hit twice in this same PR: model declares ``ondelete``, the migration
that created the table never applied it).

Mirrors the pattern from ``test_tf337_migration_safety.py`` — a full
alembic upgrade/downgrade round-trip needs its own harness pointed at a
throwaway DB and is out of scope for the regular test suite. Here the
migration does more than emit static DDL (it introspects the live schema
via ``sa.inspect``), so ``op`` *and* ``sa.inspect`` are both faked to drive
each branch of ``_find_user_fk``/``upgrade``/``downgrade`` deterministically.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "2026_08_30_tf745_fk_ondelete_cascade.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_tf745_migration_under_test", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeInspector:
    """Controls what ``sa.inspect(conn)`` returns inside the migration.

    ``tables_present``: table names ``get_table_names()`` reports.
    ``foreign_keys``: {table_name: [fk_dict, ...]} — the raw dicts
    ``inspector.get_foreign_keys(table)`` would return.
    """

    def __init__(self, tables_present, foreign_keys):
        self._tables_present = tables_present
        self._foreign_keys = foreign_keys

    def get_table_names(self):
        return self._tables_present

    def get_foreign_keys(self, table):
        return self._foreign_keys.get(table, [])


def _patch_inspection(monkeypatch, module, tables_present, foreign_keys):
    fake_op = MagicMock()
    fake_op.get_bind.return_value = object()
    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(
        module.sa,
        "inspect",
        lambda _conn: _FakeInspector(tables_present, foreign_keys),
    )
    return fake_op


_BOTH_TARGET_TABLES = ["wizard_sessions", "question_generation_jobs"]


def _fk(name: str, referred_table: str, column: str, ondelete=None) -> dict:
    return {
        "name": name,
        "referred_table": referred_table,
        "constrained_columns": [column],
        "options": {"ondelete": ondelete} if ondelete else {},
    }


def test_migration_file_exists() -> None:
    assert MIGRATION_PATH.is_file(), f"migration not found at {MIGRATION_PATH}"


def test_revision_chain_is_intact() -> None:
    """Revision/down_revision wiring — a renamed predecessor would
    silently break the upgrade chain. Pin both ends."""
    module = _load_module()
    assert module.revision == "tf745_fk_ondelete_cascade"
    assert module.down_revision == "tf740_impersonation_sessions"


def test_upgrade_fixes_missing_ondelete_for_both_targets(monkeypatch) -> None:
    """Both target tables present, FK exists but has NO ondelete policy
    (``NO ACTION``, the real pre-migration state for both) — upgrade must
    drop and recreate each FK with ``ondelete=CASCADE``."""
    module = _load_module()
    foreign_keys = {
        "wizard_sessions": [
            _fk("wizard_sessions_user_id_fkey", "users", "user_id"),
        ],
        "question_generation_jobs": [
            _fk("question_generation_jobs_user_id_fkey", "users", "user_id"),
        ],
    }
    fake_op = _patch_inspection(monkeypatch, module, _BOTH_TARGET_TABLES, foreign_keys)

    module.upgrade()

    assert fake_op.drop_constraint.call_count == 2
    assert fake_op.create_foreign_key.call_count == 2
    for call in fake_op.create_foreign_key.call_args_list:
        assert call.kwargs.get("ondelete") == "CASCADE"


def test_upgrade_skips_table_already_cascade(monkeypatch) -> None:
    """Idempotency: a re-run (or a table already fixed by a prior deploy)
    must not touch the constraint again."""
    module = _load_module()
    foreign_keys = {
        "wizard_sessions": [
            _fk(
                "wizard_sessions_user_id_fkey",
                "users",
                "user_id",
                ondelete="CASCADE",
            ),
        ],
        "question_generation_jobs": [
            _fk(
                "question_generation_jobs_user_id_fkey",
                "users",
                "user_id",
                ondelete="CASCADE",
            ),
        ],
    }
    fake_op = _patch_inspection(monkeypatch, module, _BOTH_TARGET_TABLES, foreign_keys)

    module.upgrade()

    fake_op.drop_constraint.assert_not_called()
    fake_op.create_foreign_key.assert_not_called()


def test_upgrade_skips_table_not_present(monkeypatch) -> None:
    """Core-only deployments don't have ``wizard_sessions`` (Premium) at
    all — the migration must not crash on a missing table."""
    module = _load_module()
    foreign_keys = {
        "question_generation_jobs": [
            _fk("question_generation_jobs_user_id_fkey", "users", "user_id"),
        ],
    }
    fake_op = _patch_inspection(
        monkeypatch, module, ["question_generation_jobs"], foreign_keys
    )

    module.upgrade()

    assert fake_op.drop_constraint.call_count == 1
    assert fake_op.create_foreign_key.call_count == 1


def test_upgrade_skips_when_fk_not_found(monkeypatch) -> None:
    """No matching FK (renamed away, or never existed under this name) —
    the migration defensively skips instead of raising, per its own
    ``_find_user_fk`` contract."""
    module = _load_module()
    fake_op = _patch_inspection(
        monkeypatch, module, _BOTH_TARGET_TABLES, foreign_keys={}
    )

    module.upgrade()  # must not raise

    fake_op.drop_constraint.assert_not_called()
    fake_op.create_foreign_key.assert_not_called()


def test_downgrade_reverts_cascade_to_no_policy(monkeypatch) -> None:
    module = _load_module()
    foreign_keys = {
        "wizard_sessions": [
            _fk(
                "wizard_sessions_user_id_fkey",
                "users",
                "user_id",
                ondelete="CASCADE",
            ),
        ],
        "question_generation_jobs": [
            _fk(
                "question_generation_jobs_user_id_fkey",
                "users",
                "user_id",
                ondelete="CASCADE",
            ),
        ],
    }
    fake_op = _patch_inspection(monkeypatch, module, _BOTH_TARGET_TABLES, foreign_keys)

    module.downgrade()

    assert fake_op.drop_constraint.call_count == 2
    assert fake_op.create_foreign_key.call_count == 2
    for call in fake_op.create_foreign_key.call_args_list:
        assert "ondelete" not in call.kwargs


def test_downgrade_skips_when_already_no_policy(monkeypatch) -> None:
    """Downgrade re-run safety, mirroring the upgrade idempotency test."""
    module = _load_module()
    foreign_keys = {
        "wizard_sessions": [
            _fk("wizard_sessions_user_id_fkey", "users", "user_id"),
        ],
        "question_generation_jobs": [
            _fk("question_generation_jobs_user_id_fkey", "users", "user_id"),
        ],
    }
    fake_op = _patch_inspection(monkeypatch, module, _BOTH_TARGET_TABLES, foreign_keys)

    module.downgrade()

    fake_op.drop_constraint.assert_not_called()
    fake_op.create_foreign_key.assert_not_called()
