"""Revision-chain guard for the TF-740 impersonation migration.

Mirrors test_orgunits_migration.py's chain-integrity test: alembic_version
.version_num is VARCHAR(32), so the revision id must fit, and down_revision
must chain onto the develop head it was branched from.
"""

import importlib.util
from pathlib import Path


def test_migration_revision_chain_and_id_limit():
    mig_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "2026_08_27_tf740_impersonation_sessions.py"
    )
    spec = importlib.util.spec_from_file_location("tf740_impersonation_mig", mig_path)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    assert len(mig.revision) <= 32
    assert mig.revision == "tf740_impersonation_sessions"
    assert mig.down_revision == "tf644_competency_visibility"
