"""Regression guard: ``alembic upgrade head`` must replay from an empty database (TF-434).

Until TF-434 the chain started with ``d715210cb3a3``, which ALTERs ``users``
without any migration creating it — the replay died at the first child and
local bootstraps fell back to ``create_all`` + ``stamp head``, skipping every
migration body (data seeds included). ``tf434_baseline`` is now the root.

The rest of the suite builds its schema via ``create_all`` and never runs the
real Alembic path, so this test creates its own throwaway database, runs the
whole chain in a subprocess (``alembic/env.py`` reconfigures logging, which
must not leak into the test process) and then checks:

1. The replay succeeds and ends at the single script head.
2. Migration-embedded seeds ran (tf333's system grading schemes).
3. The resulting schema matches the models, apart from a fixed list of known
   deviations (``EXPECTED_DIFFS``, empty since TF-961). The list is compared
   for equality: a new deviation fails, and so does a known one that
   disappeared.
4. Constraints that only the migration path can get wrong: prompt names are
   unique per institution, not globally (TF-961 — ``create_all`` never built
   the global unique index production had).
5. Every PK/FK/UNIQUE carries the name the models give it (TF-339) —
   autogenerate compares foreign keys by columns, not by name, so check 3
   misses a migration that names a constraint differently.
"""

import importlib
import os
import pkgutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Index, Table, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from database import Base
from db_seed import SYSTEM_GRADING_SCHEMES
from tests.test_constraint_naming_convention import (
    db_constraint_names,
    model_constraint_names,
)

_BACKEND_DIR = Path(__file__).resolve().parent.parent

# Known model/migration deviations as (kind, table, object). Empty since
# TF-961 reconciled all of them; an entry needs a comment saying why it is
# tolerated and a ticket that removes it again.
EXPECTED_DIFFS: set[tuple[str, str, str]] = set()


def _import_all_models() -> None:
    """Registers every model with ``Base`` (premium/enterprise only if mounted)."""
    for pkg_name in ("models", "premium.models", "enterprise.models"):
        try:
            pkg = importlib.import_module(pkg_name)
        except ImportError:
            continue  # core-only checkout (public mirror, core CI job)
        for mod in pkgutil.walk_packages(pkg.__path__, f"{pkg_name}."):
            importlib.import_module(mod.name)


def _diff_key(diff) -> tuple[str, str, str]:
    """Reduces an autogenerate diff entry to (kind, table, object name)."""
    if isinstance(diff, list):  # column modifications come wrapped in a list
        kind, _schema, table, column = diff[0][:4]
        return kind, table, column
    kind, obj = diff[0], diff[1]
    if isinstance(obj, Index):
        return kind, obj.table.name, obj.name
    if isinstance(obj, Table):
        return kind, obj.name, obj.name
    if kind in ("add_column", "remove_column"):
        return kind, diff[2], diff[3].name
    return (
        kind,
        str(getattr(getattr(obj, "table", None), "name", "")),
        str(getattr(obj, "name", obj)),
    )


def _insert_prompt(conn, institution_id: int, name: str) -> None:
    conn.execute(
        text(
            "INSERT INTO prompts (id, name, content, category, version, institution_id)"
            " VALUES (gen_random_uuid(), :name, 'x', 'template', 1, :inst)"
        ),
        {"name": name, "inst": institution_id},
    )


def _assert_prompt_names_unique_per_institution(conn) -> None:
    """Two institutions may share a prompt name, one institution may not (TF-961).

    Production had a global UNIQUE ``ix_prompts_name`` that only the migration
    path produced, so this can only be checked on the replayed schema.
    """
    institution_ids = [
        conn.execute(
            text(
                "INSERT INTO institutions (name, slug, is_active, subscription_tier,"
                " max_users, max_documents, max_questions_per_month)"
                " VALUES (:slug, :slug, true, 'free', 1, 5, 20) RETURNING id"
            ),
            {"slug": f"tf961-{uuid.uuid4().hex[:8]}"},
        ).scalar_one()
        for _ in range(2)
    ]
    for institution_id in institution_ids:
        _insert_prompt(conn, institution_id, "Gleicher Name")

    with pytest.raises(IntegrityError, match="ux_prompts_institution_name"):
        with conn.begin_nested():
            _insert_prompt(conn, institution_ids[0], "gleicher name")


@pytest.fixture
def empty_db_url(test_engine):
    """Creates an empty, uniquely named database and drops it afterwards."""
    name = f"alembic_empty_{uuid.uuid4().hex[:8]}"
    admin = create_engine(
        test_engine.url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield test_engine.url.set(database=name)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def test_upgrade_head_from_empty_database(empty_db_url):
    url = empty_db_url.render_as_string(hide_password=False)
    # env.py prefers DATABASE_URL over alembic.ini — point it at the empty DB.
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, (
        f"alembic upgrade head failed on an empty database:\n{result.stderr[-4000:]}"
    )

    script_head = ScriptDirectory.from_config(
        Config(str(_BACKEND_DIR / "alembic.ini"))
    ).get_current_head()

    _import_all_models()
    engine = create_engine(empty_db_url)
    try:
        with engine.connect() as conn:
            assert MigrationContext.configure(conn).get_current_revision() == (
                script_head
            )

            seeded = conn.execute(
                text(
                    "SELECT count(*) FROM grading_schemes WHERE institution_id IS NULL"
                )
            ).scalar()
            assert seeded == len(SYSTEM_GRADING_SCHEMES)

            model_tables = set(Base.metadata.tables)
            ctx = MigrationContext.configure(
                conn,
                opts={
                    "compare_type": True,
                    # Core-only: premium/enterprise tables exist in the DB
                    # (migrations create them) but not in the metadata.
                    "include_object": lambda obj, name, type_, reflected, _: (
                        type_ != "table" or name in model_tables
                    ),
                },
            )
            actual = {_diff_key(d) for d in compare_metadata(ctx, Base.metadata)}
            replayed_names = db_constraint_names(conn, model_tables)

        # prompts is created by the baseline, so it exists even core-only.
        if "prompts" in inspect(engine).get_table_names():
            with engine.connect() as conn, conn.begin() as tx:
                _assert_prompt_names_unique_per_institution(conn)
                tx.rollback()
    finally:
        engine.dispose()

    model_names = model_constraint_names()
    assert sorted(replayed_names - model_names) == [], "named only by migrations"
    assert sorted(model_names - replayed_names) == [], "named only by the models"

    expected = {key for key in EXPECTED_DIFFS if key[1] in model_tables}
    unexpected = sorted(actual - expected)
    vanished = sorted(expected - actual)
    assert not unexpected and not vanished, (
        "Schema from `alembic upgrade head` deviates from the models.\n"
        f"New deviations (add a migration or fix the model): {unexpected}\n"
        f"Known deviations that disappeared (remove from EXPECTED_DIFFS): {vanished}"
    )
