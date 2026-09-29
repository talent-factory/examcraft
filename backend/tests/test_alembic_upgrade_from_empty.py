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
   deviations (``EXPECTED_DIFFS``). The list is compared for equality: a new
   deviation fails, and so does a known one that disappeared — remove it from
   the list in the PR that fixes it (TF-961).
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
from sqlalchemy import Index, Table, create_engine, text

from database import Base
from db_seed import SYSTEM_GRADING_SCHEMES

_BACKEND_DIR = Path(__file__).resolve().parent.parent

# Known model/migration deviations as (kind, table, object). Each group names
# why it is tolerated; none of them may be dropped silently.
EXPECTED_DIFFS = {
    # TF-961 #1: the original ``unique=True`` created a UNIQUE *index*, tf346
    # only drops the (non-existent) ``prompts_name_key`` constraint. Production
    # has the same global unique index (verified read-only 2026-09-29).
    ("remove_index", "prompts", "ix_prompts_name"),
    ("add_index", "prompts", "ix_prompts_name"),
    # TF-961 #2: b2c3d4e5f6a7 adds resource_usage.institution_id nullable and
    # without its own index; the model wants NOT NULL + index=True.
    ("modify_nullable", "resource_usage", "institution_id"),
    ("add_index", "resource_usage", "ix_resource_usage_institution_id"),
    # TF-961 #3: ``index=True`` on a primary key, never created by a migration.
    ("add_index", "competencies", "ix_competencies_id"),
    ("add_index", "competency_frameworks", "ix_competency_frameworks_id"),
    ("add_index", "feedback_clusters", "ix_feedback_clusters_id"),
    ("add_index", "moodle_feedback_push_jobs", "ix_moodle_feedback_push_jobs_id"),
    # Indexes that only exist in migrations (partial / functional / DESC), the
    # models do not declare them. Production has them; create_all-built
    # databases (dev, test suite) do not. Covered by TF-961's acceptance
    # criterion "compare_metadata reports 0 deviations".
    ("remove_index", "audit_logs", "ix_audit_logs_user_id_created_at_desc"),
    ("remove_index", "document_tags", "ix_document_tags_tag_id"),
    ("remove_index", "documents", "ix_documents_inst_vis_created"),
    ("remove_index", "documents", "ix_documents_pending_reindex"),
    ("remove_index", "exams", "ix_exams_archived_at"),
    ("remove_index", "exams", "ix_exams_inst_vis_updated"),
    ("remove_index", "grading_schemes", "uq_grading_schemes_system_name"),
    ("remove_index", "institutions", "uq_institutions_single_system"),
    ("remove_index", "org_units", "ix_org_units_unique_root_name"),
    ("remove_index", "org_units", "ix_org_units_unique_sibling_name"),
    ("remove_index", "question_reviews", "ix_question_reviews_inst_vis_created"),
    ("remove_index", "tags", "uix_global_tag_name_lower"),
    ("remove_index", "tags", "uix_tag_name_lower_institution"),
}


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
    finally:
        engine.dispose()

    expected = {key for key in EXPECTED_DIFFS if key[1] in model_tables}
    unexpected = sorted(actual - expected)
    vanished = sorted(expected - actual)
    assert not unexpected and not vanished, (
        "Schema from `alembic upgrade head` deviates from the models.\n"
        f"New deviations (add a migration or fix the model): {unexpected}\n"
        f"Known deviations that disappeared (remove from EXPECTED_DIFFS): {vanished}"
    )
