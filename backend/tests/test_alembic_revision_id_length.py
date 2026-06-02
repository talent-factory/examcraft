"""Regressions-Guard: Alembic-Revision-IDs müssen in alembic_version passen.

Alembic legt die Tabelle `alembic_version` standardmässig mit
`version_num VARCHAR(32)` an. Eine Revision-ID > 32 Zeichen lässt sich
weder per `upgrade` noch per `stamp` schreiben — Postgres bricht mit
`StringDataRightTruncation` ab. Genau das war der Release-Blocker in TF-388
(`tf383_question_generation_metadata`, 34 Zeichen).

Dieser Test scannt die Migrationsdateien direkt (ohne DB/Alembic-Import) und
schlägt fehl, sobald eine `revision`-ID die Grenze überschreitet — fängt den
Fehler also vor dem Merge ab, ohne den vollen Migrationspfad fahren zu müssen.
"""

import re
from pathlib import Path

# Default-Breite der Spalte alembic_version.version_num
ALEMBIC_VERSION_NUM_MAX = 32

_VERSIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"
_REVISION_RE = re.compile(r'^revision(?:\s*:\s*\w+)?\s*=\s*["\']([^"\']+)["\']', re.M)


def _iter_revisions():
    """Liefert (Dateiname, revision_id) für jede Migrationsdatei mit revision."""
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
