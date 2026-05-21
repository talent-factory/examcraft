"""Lightweight safety-checks for the tf333_phase1 migration.

A full upgrade/downgrade round-trip is out of scope for the test suite
(requires its own alembic harness pointed at a throwaway DB). This file
exercises the parts that can be checked statically + the env-gate on
the destructive downgrade path.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "2026_04_30_tf333_auswertungen_phase1.py"
)


def test_migration_file_exists() -> None:
    assert MIGRATION_PATH.is_file(), f"migration not found at {MIGRATION_PATH}"


def test_unique_constraint_on_attempts_is_tenant_scoped() -> None:
    """Static check: the (institution_id, source, source_attempt_id)
    unique constraint must exist verbatim in the migration source.

    Locks in the cross-tenant idempotency fix — a future maintainer
    dropping institution_id from the constraint would re-introduce
    the cross-tenant collision bug.
    """
    text = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "uq_attempts_inst_source_attempt_id" in text
    assert '"institution_id",\n            "source",' in text


def test_destructive_downgrade_requires_env_gate(monkeypatch) -> None:
    """The downgrade drops every Phase-1 row. With AUTO_MIGRATE=true in
    prod the operator has no chance to take a backup before container
    start, so the downgrade refuses to run unless explicitly opted in.
    """
    # Load the module via importlib so we get the actual downgrade fn
    # rather than re-running it as a script.
    monkeypatch.delenv("ALEMBIC_ALLOW_DESTRUCTIVE_DOWNGRADE", raising=False)
    spec = importlib.util.spec_from_file_location(
        "_tf333_migration_under_test", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Stub `op` and `sa` to no-ops so the import doesn't blow up because
    # of the alembic context not being active.
    spec.loader.exec_module(module)

    with pytest.raises(RuntimeError, match="ALEMBIC_ALLOW_DESTRUCTIVE_DOWNGRADE"):
        module.downgrade()


def test_destructive_downgrade_proceeds_with_env_gate(monkeypatch) -> None:
    """With the env var set, downgrade proceeds past the guard. We mock
    out alembic.op so the test doesn't need a live connection."""
    monkeypatch.setenv("ALEMBIC_ALLOW_DESTRUCTIVE_DOWNGRADE", "1")

    spec = importlib.util.spec_from_file_location(
        "_tf333_migration_gate_test", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    from unittest.mock import MagicMock

    fake_op = MagicMock()
    monkeypatch.setattr(module, "op", fake_op)

    # Should not raise the env-gate RuntimeError. May still raise other
    # errors when the mocked op chain hits something unexpected; we only
    # assert the gate itself does not block.
    try:
        module.downgrade()
    except RuntimeError as exc:
        if "ALEMBIC_ALLOW_DESTRUCTIVE_DOWNGRADE" in str(exc):
            pytest.fail("env gate must let downgrade through when set to 1")
    except Exception:
        # Anything else means we got past the gate, which is what we test.
        pass
    finally:
        os.environ.pop("ALEMBIC_ALLOW_DESTRUCTIVE_DOWNGRADE", None)
