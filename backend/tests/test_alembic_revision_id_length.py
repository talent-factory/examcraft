"""Regression guard: Alembic revision IDs must fit in alembic_version.

Alembic creates the `alembic_version` table by default with
`version_num VARCHAR(32)`. A revision ID > 32 characters can be written
neither via `upgrade` nor via `stamp` — Postgres aborts with
`StringDataRightTruncation`. That was exactly the release blocker in TF-388
(`tf383_question_generation_metadata`, 34 characters).

This test scans the migration files directly (without a DB/Alembic import)
and fails as soon as a `revision` ID exceeds the limit — catching the
error before the merge, without having to run the full migration path.
"""

import re
from pathlib import Path

# Default width of the alembic_version.version_num column
ALEMBIC_VERSION_NUM_MAX = 32

_VERSIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"
_REVISION_RE = re.compile(r'^revision(?:\s*:\s*\w+)?\s*=\s*["\']([^"\']+)["\']', re.M)


def _iter_revisions():
    """Yields (filename, revision_id) for every migration file that has a revision."""
    for path in sorted(_VERSIONS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        match = _REVISION_RE.search(path.read_text(encoding="utf-8"))
        if match:
            yield path.name, match.group(1)


def test_versions_dir_exists_and_has_migrations():
    assert _VERSIONS_DIR.is_dir(), f"alembic versions dir missing: {_VERSIONS_DIR}"
    assert list(_iter_revisions()), "no alembic revisions found to validate"


def test_all_revision_ids_fit_alembic_version_column():
    too_long = [
        (name, rev, len(rev))
        for name, rev in _iter_revisions()
        if len(rev) > ALEMBIC_VERSION_NUM_MAX
    ]
    assert not too_long, (
        "Alembic revision id(s) exceed alembic_version.version_num "
        f"VARCHAR({ALEMBIC_VERSION_NUM_MAX}) and will fail to apply/stamp "
        "(psycopg2 StringDataRightTruncation):\n"
        + "\n".join(f"  {name}: '{rev}' ({n} chars)" for name, rev, n in too_long)
    )
