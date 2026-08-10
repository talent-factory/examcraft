"""Revision-chain guard for the org_units/user_org_units migration.

Mirrors test_tf403_migration.py's chain-integrity test: alembic_version.version_num
is VARCHAR(32) so the revision id must fit, and down_revision must chain onto the
develop head it was branched from.
"""

import importlib.util
from pathlib import Path


def test_migration_revision_chain_and_id_limit():
    mig_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "2026_08_07_orgunits_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("orgunits_foundation_mig", mig_path)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    assert len(mig.revision) <= 32
    assert mig.revision == "orgunits_foundation"
    assert mig.down_revision == "tf500_attempt_idem_exam"
