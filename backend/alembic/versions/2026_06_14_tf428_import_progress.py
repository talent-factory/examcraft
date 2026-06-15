"""tf428: Live-Fortschritt für Resultatimport (graded_total / graded_done)

Der Resultatimport (TF-412/TF-423) bewertet Freitextfragen seriell per LLM und
kann Minuten dauern. Damit die UI «n/total bewertet» statt eines opaken Spinners
zeigt (TF-428), bekommt ``import_jobs`` zwei Fortschritts-Spalten:

- ``graded_total``: Anzahl zu bewertender Submissions (NULL solange geparst wird).
- ``graded_done``: Anzahl bereits verarbeiteter Submissions (bewertet oder
  fehlgeschlagen; Default 0).

Additiv und nicht-destruktiv: zwei neue Spalten, Altbestand erhält ``graded_done``
= 0 über das server_default — unbedenklich unter AUTO_MIGRATE=true.

Revision ID: tf428_import_progress
Revises: tf423_moodle_json_driver
Create Date: 2026-06-14
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf428_import_progress"
down_revision: Union[str, None] = "tf423_moodle_json_driver"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "import_jobs",
        sa.Column("graded_total", sa.Integer(), nullable=True),
    )
    op.add_column(
        "import_jobs",
        sa.Column(
            "graded_done",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # Drop the server_default after backfilling existing rows: the ORM sets the
    # value explicitly on every write, the default was only needed so the
    # NOT NULL column could be added to a populated table in one statement.
    op.alter_column("import_jobs", "graded_done", server_default=None)


def downgrade() -> None:
    op.drop_column("import_jobs", "graded_done")
    op.drop_column("import_jobs", "graded_total")
