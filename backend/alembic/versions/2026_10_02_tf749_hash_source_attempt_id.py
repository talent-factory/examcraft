"""attempts.source_attempt_id: replace e-mail-based keys with SHA-256 (TF-749)

The Moodle JSON driver composed the idempotency key as
``email|started_at|N`` (or ``email|h:<content hash>``) and stored it in
plain text, so every attempt row, the submissions API and import logs
carried the student's e-mail address. The driver now stores
``sha256:<hex>`` of that composed key
(``MoodleJsonDriver.hash_source_attempt_key``). This revision applies the
same function to existing rows, otherwise a re-import of an already
imported Moodle export would no longer recognise its attempts and import
them a second time.

Covers ``moodle_json`` and the historical ``moodle_csv`` rows (TF-423
removed that driver; its keys embedded the e-mail as well). ``moodle_api``
keys are Moodle's numeric attempt ids and stay unchanged.

Idempotent (rows already prefixed with ``sha256:`` are skipped), plain
statements inside the migration transaction — safe for
``AUTO_MIGRATE=true`` deploys.

Downgrade is a no-op: a hash cannot be turned back into the e-mail. After
a downgrade the old driver would compose plain keys again and a re-import
of an already imported export would duplicate its attempts.

Revision ID: tf749_hash_source_attempt_id
Revises: tf986_document_managed_by
Create Date: 2026-10-02 12:00:00.000000
"""

import hashlib
import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf749_hash_source_attempt_id"
down_revision: Union[str, None] = "tf986_document_managed_by"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match services.import_drivers.moodle_json_driver.hash_source_attempt_key
# (a test pins both together). Copied rather than imported so the migration
# keeps working when the driver changes.
_PREFIX = "sha256:"
_SOURCES = ("moodle_json", "moodle_csv")


def hash_source_attempt_key(key: str) -> str:
    if key.startswith(_PREFIX):
        return key
    return _PREFIX + hashlib.sha256(key.encode()).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, source_attempt_id FROM attempts "
            "WHERE source IN :sources AND source_attempt_id IS NOT NULL "
            "AND source_attempt_id NOT LIKE :prefix"
        ).bindparams(sa.bindparam("sources", expanding=True)),
        {"sources": list(_SOURCES), "prefix": _PREFIX + "%"},
    ).fetchall()
    if not rows:
        return
    bind.execute(
        sa.text("UPDATE attempts SET source_attempt_id = :new WHERE id = :id"),
        [
            {"id": row.id, "new": hash_source_attempt_key(row.source_attempt_id)}
            for row in rows
        ],
    )


def downgrade() -> None:
    # Irreversible by design, see module docstring.
    logging.getLogger("alembic.runtime.migration").warning(
        "tf749_hash_source_attempt_id: Downgrade lässt source_attempt_id gehasht; "
        "ein Re-Import bereits importierter Moodle-Exporte dupliziert Versuche."
    )
