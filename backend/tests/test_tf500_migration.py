"""Safety-checks for the tf500 attempt-idempotency re-scope migration.

A full upgrade/downgrade round-trip against a live DB is out of scope for
the suite (CI runs against the ``create_all`` schema, not the migration
path — see project memory). This file pins the migration's *contract*
statically and via a mocked ``alembic.op`` so a future edit that silently
re-scopes the idempotency key back to institution-wide — re-introducing the
TF-500 cross-exam collision — fails here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "2026_06_30_tf500_attempt_idempotency_exam_scoped.py"
)

_OLD_CONSTRAINT = "uq_attempts_inst_source_attempt_id"
_NEW_CONSTRAINT = "uq_attempts_submission_source_attempt_id"
_OLD_LOOKUP_INDEX = "ix_attempts_inst_source_lookup"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "_tf500_migration_under_test", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_file_exists() -> None:
    assert MIGRATION_PATH.is_file(), f"migration not found at {MIGRATION_PATH}"


def test_revision_metadata() -> None:
    module = _load_module()
    # Revision id must stay ≤32 chars (alembic_version is VARCHAR(32)).
    assert module.revision == "tf500_attempt_idem_exam"
    assert len(module.revision) <= 32
    assert module.down_revision == "tf439_grade_logical"


def test_upgrade_scopes_unique_constraint_to_submission(monkeypatch) -> None:
    """The new unique constraint must be ``(submission_id, source,
    source_attempt_id)`` — per exam+student, NOT institution-wide.

    This is the load-bearing assertion: dropping ``submission_id`` (or
    re-adding ``institution_id``) would re-introduce the cross-exam
    idempotency collision TF-500 fixes.
    """
    module = _load_module()
    fake_op = MagicMock()
    monkeypatch.setattr(module, "op", fake_op)

    module.upgrade()

    # Old institution-scoped lookup index + constraint are removed.
    fake_op.drop_index.assert_called_once_with(_OLD_LOOKUP_INDEX, table_name="attempts")
    fake_op.drop_constraint.assert_called_once_with(
        _OLD_CONSTRAINT, "attempts", type_="unique"
    )
    # New constraint is submission-scoped.
    fake_op.create_unique_constraint.assert_called_once_with(
        _NEW_CONSTRAINT,
        "attempts",
        ["submission_id", "source", "source_attempt_id"],
    )


def test_downgrade_restores_institution_scoped_key(monkeypatch) -> None:
    """Downgrade reverses cleanly: new constraint dropped, old
    institution-scoped constraint + lookup index re-created."""
    module = _load_module()
    fake_op = MagicMock()
    monkeypatch.setattr(module, "op", fake_op)

    module.downgrade()

    fake_op.drop_constraint.assert_called_once_with(
        _NEW_CONSTRAINT, "attempts", type_="unique"
    )
    fake_op.create_unique_constraint.assert_called_once_with(
        _OLD_CONSTRAINT,
        "attempts",
        ["institution_id", "source", "source_attempt_id"],
    )
    fake_op.create_index.assert_called_once_with(
        _OLD_LOOKUP_INDEX,
        "attempts",
        ["institution_id", "source", "source_attempt_id"],
    )


def test_downgrade_data_loss_hazard_is_documented() -> None:
    """The downgrade can fail on data that the new schema legitimately
    allows (same attempt in two exams). Keep that warning in the source so
    an operator running the downgrade is forewarned."""
    text = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "TF-500 enables" in text
    assert "resolve the duplicates" in text


@pytest.mark.parametrize("fn_name", ["upgrade", "downgrade"])
def test_migration_defines_callables(fn_name: str) -> None:
    module = _load_module()
    assert callable(getattr(module, fn_name))
