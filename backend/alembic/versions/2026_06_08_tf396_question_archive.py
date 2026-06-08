"""tf396: Archiv-Achse (archived_at/by/reason) auf question_reviews

Orthogonal zum review_status. archived_at IS NULL => aktiv; gesetzt =>
archiviert (aus Bank/Listen ausgeblendet, in Prüfungen aber erhalten).
Additive, nullable Spalten + partieller Index — nicht-destruktiv, unbedenklich
unter AUTO_MIGRATE=true. Altbestand bleibt NULL ("aktiv"). (TF-396)

Revision ID: tf396_question_archive
Revises: tf383_question_gen_metadata
Create Date: 2026-06-08
"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "tf396_question_archive"
down_revision: Union[str, None] = "tf383_question_gen_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "question_reviews",
        sa.Column("archived_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "question_reviews",
        sa.Column("archived_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "question_reviews",
        sa.Column("archive_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_question_reviews_archived_by_users",
        "question_reviews",
        "users",
        ["archived_by"],
        ["id"],
        ondelete="SET NULL",
    )
    # Partieller Index NUR auf archivierte Zeilen (archived_at IS NOT NULL):
    # beschleunigt die Archiv-/Admin-Aufräumansicht (archived_only). Der
    # Default-Filter (archived_at IS NULL) profitiert NICHT von diesem Index —
    # Postgres nutzt einen partiellen Index nur, wenn das Query-Prädikat das
    # Index-Prädikat impliziert; IS NULL schliesst alle indizierten Zeilen aus.
    # Bewusst so: die archivierte Menge ist klein und selektiv, die aktive
    # (IS NULL) gross und unselektiv. Plain CREATE INDEX (kein CONCURRENTLY —
    # würde In-Transaction-Migrationstests brechen).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_question_reviews_archived_at "
        "ON question_reviews (archived_at) WHERE archived_at IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_question_reviews_archived_at")
    op.drop_constraint(
        "fk_question_reviews_archived_by_users",
        "question_reviews",
        type_="foreignkey",
    )
    op.drop_column("question_reviews", "archive_reason")
    op.drop_column("question_reviews", "archived_by")
    op.drop_column("question_reviews", "archived_at")
