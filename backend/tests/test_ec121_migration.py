"""Guards for the EXAMCRAFT-121 migration (users.zitadel_sub).

alembic_version.version_num is VARCHAR(32), and the revision must chain onto
the previous head. The model must match the migration (nullable, unique,
indexed).
"""

import importlib.util
from pathlib import Path

from models.auth import User


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "2026_11_13_ec121_users_zitadel_sub.py"
    )
    spec = importlib.util.spec_from_file_location("ec121_users_zitadel_sub_mig", path)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    return mig


def test_migration_revision_chain_and_id_limit():
    mig = _load_migration()

    assert len(mig.revision) <= 32
    assert mig.revision == "ec121_users_zitadel_sub"
    assert mig.down_revision == "tf1060_previous_login_at"


def test_model_column_is_nullable_unique_and_indexed():
    column = User.__table__.c.zitadel_sub

    assert column.nullable is True
    assert column.unique is True
    assert column.index is True
