"""Enforce tag ``scope`` value set + institution/global name uniqueness (TF-372).

Closes two gaps left by the TF-355 tag work:

1. ``tags.scope`` was a free ``VARCHAR`` — the valid set (``user`` /
   ``institution`` / ``global``) lived only as scattered string literals.
   Adds a ``ck_tags_scope_valid`` CHECK so illegal scopes are unrepresentable.
2. Only ``user``-scope names were unique (``ux_tags_user_name``).
   ``institution``/``global`` names had no DB backstop, so the get-or-create
   endpoint's 409-on-duplicate branch could never fire (TOCTOU race). Adds the
   two partial unique indexes that mirror the Tag model's ``__table_args__``.

⚠️  Pre-step: because a unique index would FAIL on pre-existing duplicates and
abort an ``AUTO_MIGRATE`` deploy, this migration first DEDUPLICATES existing
institution/global tags (case-insensitive). It keeps the lowest-id tag per
``(scope, institution_id, lower(name))`` group, re-points ``question_tags`` and
``document_tags`` links to the survivor (dropping links that would collide),
then deletes the redundant tag rows. The dedup is data-preserving (no link is
lost, only deduplicated) — mirrors the TF-369 transfer-time dedup logic.

All statements are plain (no ``CONCURRENTLY``/autocommit) so the migration runs
inside a single transaction and stays compatible with the in-transaction
migration tests. Idempotent: CHECK guarded by a ``pg_constraint`` probe,
indexes by ``IF NOT EXISTS``; the dedup is a no-op when there are no duplicates.

Revision ID: tf372_tags_scope_uniqueness
Revises: tf355_document_tags
"""

from typing import Union

from alembic import op

revision: str = "tf372_tags_scope_uniqueness"
down_revision: Union[str, None] = "tf355_document_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Build a dup_id -> survivor_id map for institution + global scopes.
    #    institution groups by (institution_id, lower(name)); global by
    #    lower(name) only. The temp table is dropped at transaction end.
    op.execute(
        """
        CREATE TEMP TABLE _tag_dedup_map ON COMMIT DROP AS
        SELECT t.id AS dup_id, m.survivor_id
        FROM tags t
        JOIN (
            SELECT
                scope,
                CASE WHEN scope = 'institution' THEN institution_id END AS inst,
                lower(name) AS lname,
                min(id) AS survivor_id
            FROM tags
            WHERE scope IN ('institution', 'global')
            GROUP BY
                scope,
                CASE WHEN scope = 'institution' THEN institution_id END,
                lower(name)
        ) m
          ON t.scope = m.scope
         AND lower(t.name) = m.lname
         AND (
             (t.scope = 'institution'
              AND t.institution_id IS NOT DISTINCT FROM m.inst)
             OR t.scope = 'global'
         )
        WHERE t.id <> m.survivor_id;
        """
    )

    # 2. Re-point links to the survivor. Drop links that would collide with an
    #    already-present survivor link first (composite PK), then update the rest.
    op.execute(
        """
        DELETE FROM question_tags qt
        USING _tag_dedup_map d
        WHERE qt.tag_id = d.dup_id
          AND EXISTS (
              SELECT 1 FROM question_tags qt2
              WHERE qt2.question_id = qt.question_id
                AND qt2.tag_id = d.survivor_id
          );
        """
    )
    op.execute(
        """
        UPDATE question_tags qt
        SET tag_id = d.survivor_id
        FROM _tag_dedup_map d
        WHERE qt.tag_id = d.dup_id;
        """
    )
    op.execute(
        """
        DELETE FROM document_tags dt
        USING _tag_dedup_map d
        WHERE dt.tag_id = d.dup_id
          AND EXISTS (
              SELECT 1 FROM document_tags dt2
              WHERE dt2.document_id = dt.document_id
                AND dt2.tag_id = d.survivor_id
          );
        """
    )
    op.execute(
        """
        UPDATE document_tags dt
        SET tag_id = d.survivor_id
        FROM _tag_dedup_map d
        WHERE dt.tag_id = d.dup_id;
        """
    )

    # 3. Delete the now-orphaned duplicate tag rows.
    op.execute("DELETE FROM tags t USING _tag_dedup_map d WHERE t.id = d.dup_id;")

    # 4. Scope CHECK constraint (guarded — no ADD CONSTRAINT IF NOT EXISTS in PG).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_tags_scope_valid'
            ) THEN
                ALTER TABLE tags
                    ADD CONSTRAINT ck_tags_scope_valid
                    CHECK (scope IN ('user', 'institution', 'global'));
            END IF;
        END $$;
        """
    )

    # 5. Partial unique indexes — mirror the Tag model's __table_args__.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_institution_name "
        "ON tags (institution_id, LOWER(name)) WHERE scope = 'institution'"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_global_name "
        "ON tags (LOWER(name)) WHERE scope = 'global'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_tags_global_name")
    op.execute("DROP INDEX IF EXISTS ux_tags_institution_name")
    op.execute("ALTER TABLE tags DROP CONSTRAINT IF EXISTS ck_tags_scope_valid")
    # Dedup is not reversible (the duplicate rows are gone) — nothing to undo.
