"""tf398: Archiv-Achse (archived_at/by/reason) auf exams

Orthogonal zum status (draft/finalized/exported). archived_at IS NULL =>
aktiv; gesetzt => archiviert (aus der aktiven Komponist-Übersicht
ausgeblendet, status bleibt unangetastet). Additive, nullable Spalten +
partieller Index — nicht-destruktiv, unbedenklich unter AUTO_MIGRATE=true.
Altbestand bleibt NULL ("aktiv"). Spiegelt das TF-396-Muster
(question_reviews). (TF-398)

Revision ID: tf398_exam_archive
Revises: tf397_prompt_template_tags
Create Date: 2026-06-10
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf398_exam_archive"
# Rebased von tf396 auf tf397 (develop-Head), um nach dem Merge von
# develop einen Multi-Head zu vermeiden — tf400/401/402/397 hängen
# ebenfalls an tf396, daher reiht sich tf398 hinter den develop-Head.
down_revision: Union[str, None] = "tf397_prompt_template_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exams",
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "exams",
        sa.Column("archived_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "exams",
        sa.Column("archive_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_exams_archived_by_users",
        "exams",
        "users",
        ["archived_by"],
        ["id"],
        ondelete="SET NULL",
    )
    # Partieller Index NUR auf archivierte Zeilen (archived_at IS NOT NULL):
    # beschleunigt die Archiv-Übersicht (archived_only). Der Default-Filter
    # (archived_at IS NULL) profitiert NICHT von diesem Index — Postgres nutzt
    # einen partiellen Index nur, wenn das Query-Prädikat das Index-Prädikat
    # impliziert; IS NULL schliesst alle indizierten Zeilen aus. Bewusst so:
    # die archivierte Menge ist klein und selektiv, die aktive (IS NULL) gross
    # und unselektiv. Plain CREATE INDEX (kein CONCURRENTLY — würde
    # In-Transaction-Migrationstests brechen).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_exams_archived_at "
        "ON exams (archived_at) WHERE archived_at IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_exams_archived_at")
    op.drop_constraint(
        "fk_exams_archived_by_users",
        "exams",
        type_="foreignkey",
    )
    op.drop_column("exams", "archive_reason")
    op.drop_column("exams", "archived_by")
    op.drop_column("exams", "archived_at")
