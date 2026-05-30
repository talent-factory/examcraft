"""Add ``visibility`` enum to documents (TF-354 privacy fix).

Closes a privacy gap: the document list previously filtered only by
``institution_id``, so every member of an institution saw every colleague's
uploads. The new ``visibility`` column makes the default ``private`` (owner
only); a document is shared institution-wide only when its owner explicitly
sets ``institution``.

Steps:
1. Create the ``documentvisibility`` enum (``private``/``institution``).
2. Add ``documents.visibility`` NOT NULL DEFAULT ``private``. Existing rows
   inherit the default — security-first: nothing becomes more visible by the
   migration. On PG 11+ a constant-DEFAULT column add is metadata-only (no
   table rewrite), so the backfill is cheap; no explicit ``UPDATE`` is issued
   (the default already sets every existing row to ``private``).
3. CHECK constraint ``ck_documents_institution_visibility_requires_institution``
   (``visibility <> 'institution' OR institution_id IS NOT NULL``) — makes the
   "shared ⇒ has institution" invariant unrepresentable at the DB level. Added
   while every row is ``private``, so nothing violates it.
4. Single-column index ``ix_documents_visibility`` and composite
   ``ix_documents_inst_vis_created`` on
   ``(institution_id, visibility, created_at DESC)`` — backs the main list
   query (filter by institution + visibility, ORDER BY created_at DESC). Plain
   (non-CONCURRENTLY) ``CREATE INDEX`` — same call made in
   ``tf337_audit_logs_idx``: the build takes a brief write lock, acceptable
   because ``documents`` is small in prod. If the table grows by orders of
   magnitude, reissue these CONCURRENTLY in a hand-rolled SQL step.

Additive and idempotent (enum + constraint guarded by DO blocks, column/indexes
guarded by ``IF NOT EXISTS``). Safe for ``AUTO_MIGRATE=true`` deploys — no manual
step.

Revision ID: tf354_documents_visibility
Revises: tf352_documents_pending_reindex
"""

from typing import Union

from alembic import op


revision: str = "tf354_documents_visibility"
down_revision: Union[str, None] = "tf352_documents_pending_reindex"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enum type. CREATE TYPE has no IF NOT EXISTS — guard with a DO block so
    #    a re-run (or a type left behind by a half-applied downgrade) is a no-op.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'documentvisibility'
            ) THEN
                CREATE TYPE documentvisibility AS ENUM ('private', 'institution');
            END IF;
        END$$;
        """
    )

    # 2. Column — NOT NULL with a server default backfills existing rows to
    #    'private'. On PG 11+ this is a metadata-only operation (no rewrite);
    #    the default covers every existing row, so no explicit UPDATE is needed.
    op.execute(
        "ALTER TABLE documents "
        "ADD COLUMN IF NOT EXISTS visibility documentvisibility "
        "NOT NULL DEFAULT 'private'"
    )

    # 3. Invariant: an institution-visible document must belong to an institution.
    #    Postgres has no ADD CONSTRAINT IF NOT EXISTS, so guard with a DO block.
    #    Every row is 'private' after step 2, so none violate it.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname =
                    'ck_documents_institution_visibility_requires_institution'
            ) THEN
                ALTER TABLE documents
                    ADD CONSTRAINT
                        ck_documents_institution_visibility_requires_institution
                    CHECK (visibility <> 'institution' OR institution_id IS NOT NULL);
            END IF;
        END$$;
        """
    )

    # 4. Indexes. Plain CREATE INDEX (runs inside the migration transaction),
    #    matching tf337_audit_logs_idx: ``documents`` is small in prod, so the
    #    brief write lock is acceptable. Reissue CONCURRENTLY by hand if the
    #    table ever grows by orders of magnitude.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_visibility ON documents (visibility)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_inst_vis_created "
        "ON documents (institution_id, visibility, created_at DESC)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE documents DROP CONSTRAINT IF EXISTS "
        "ck_documents_institution_visibility_requires_institution"
    )
    op.execute("DROP INDEX IF EXISTS ix_documents_inst_vis_created")
    op.execute("DROP INDEX IF EXISTS ix_documents_visibility")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS visibility")
    op.execute("DROP TYPE IF EXISTS documentvisibility")
