"""TF-397: unify prompt-template tags with the managed Tag system.

Adds a ``kind`` namespace dimension to ``tags`` (``content`` | ``prompt``),
folds ``kind`` into the partial unique indexes, and introduces the
``prompt_tags`` join table linking premium Prompts to managed ``kind='prompt'``
tags. Existing free-text ``prompts.tags`` ARRAY values are backfilled into
normalized managed tags + links.

Design / constraints (per project conventions):
- Single in-transaction revision, plain ``CREATE INDEX`` (no CONCURRENTLY).
- Revision id <= 32 chars.
- ``prompt_tags`` creation + backfill are GUARDED on the ``prompts`` table
  existing, because ``prompts`` is a premium model created via ``create_all``
  only when premium is mounted. In core-only deployments ``prompts`` is absent,
  so this migration is a no-op for the join table there.
- Idempotent (IF NOT EXISTS / inspector guards / ON CONFLICT) so it tolerates
  partially-applied state.

The free-text normalization mirrors ``utils.tag_normalize.normalize_prompt_tag_name``:
trim -> lowercase -> collapse runs of ``-``/whitespace to a single ``_``.

Revision ID: tf397_prompt_template_tags
Revises: tf402_ln_level_check
Create Date: 2026-06-10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "tf397_prompt_template_tags"
down_revision = "tf402_ln_level_check"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 1. tags.kind column ------------------------------------------------
    # ADD COLUMN ... NOT NULL DEFAULT backfills existing rows to 'content' in
    # one statement; drop the server default afterwards to match the model
    # (which uses a Python-side default only).
    op.execute(
        "ALTER TABLE tags ADD COLUMN IF NOT EXISTS kind VARCHAR(20) "
        "NOT NULL DEFAULT 'content'"
    )
    op.execute("ALTER TABLE tags ALTER COLUMN kind DROP DEFAULT")

    # --- 2. kind CHECK constraint (closed value set) ------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_tags_kind_valid'
            ) THEN
                ALTER TABLE tags
                    ADD CONSTRAINT ck_tags_kind_valid
                    CHECK (kind IN ('content', 'prompt'));
            END IF;
        END $$;
        """
    )

    # --- 3. rebuild partial unique indexes to include kind ------------------
    # Uniqueness becomes per (scope, kind, lower(name)) so a 'prompt'-kind tag
    # may coexist with a 'content'-kind tag of the same name in the same scope.
    op.execute("DROP INDEX IF EXISTS ux_tags_user_name")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_user_name "
        "ON tags (created_by, kind, lower(name)) WHERE scope = 'user'"
    )
    op.execute("DROP INDEX IF EXISTS ux_tags_institution_name")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_institution_name "
        "ON tags (institution_id, kind, lower(name)) WHERE scope = 'institution'"
    )
    op.execute("DROP INDEX IF EXISTS ux_tags_global_name")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_global_name "
        "ON tags (kind, lower(name)) WHERE scope = 'global'"
    )

    # --- 4. prompt_tags join + backfill (premium only) ----------------------
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "prompts" not in existing_tables:
        # Core-only deployment: no Prompt model, nothing to link. Done.
        return

    if "prompt_tags" not in existing_tables:
        op.create_table(
            "prompt_tags",
            sa.Column("prompt_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("prompt_id", "tag_id"),
        )

    # Backfill: create the managed prompt-kind tags from normalized array values
    # (separator variants collapse onto one tag), then link each prompt.
    op.execute(
        r"""
        INSERT INTO tags (name, scope, kind, usage_count, is_archived, created_at)
        SELECT DISTINCT
               lower(regexp_replace(btrim(t.val), '[-\s]+', '_', 'g')),
               'global', 'prompt', 0, false, now()
        FROM prompts p
        CROSS JOIN LATERAL unnest(p.tags) AS t(val)
        WHERE p.tags IS NOT NULL
          AND btrim(t.val) <> ''
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        r"""
        INSERT INTO prompt_tags (prompt_id, tag_id, created_at)
        SELECT DISTINCT p.id, tg.id, now()
        FROM prompts p
        CROSS JOIN LATERAL unnest(p.tags) AS t(val)
        JOIN tags tg
          ON tg.scope = 'global'
         AND tg.kind = 'prompt'
         AND tg.name = lower(regexp_replace(btrim(t.val), '[-\s]+', '_', 'g'))
        WHERE p.tags IS NOT NULL
          AND btrim(t.val) <> ''
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    # Drop the join table first (guarded — may not exist in core-only).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "prompt_tags" in set(inspector.get_table_names()):
        op.drop_table("prompt_tags")

    # Remove the prompt-kind tags this migration introduced. They only exist
    # because of TF-397, and they must go before the kind-less unique indexes
    # can be restored — otherwise a prompt 'default' and a content 'default'
    # would collide on the (lower(name)) global index.
    op.execute("DELETE FROM tags WHERE kind = 'prompt'")

    # Restore the original (kind-less) partial unique indexes.
    op.execute("DROP INDEX IF EXISTS ux_tags_user_name")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_user_name "
        "ON tags (created_by, lower(name)) WHERE scope = 'user'"
    )
    op.execute("DROP INDEX IF EXISTS ux_tags_institution_name")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_institution_name "
        "ON tags (institution_id, lower(name)) WHERE scope = 'institution'"
    )
    op.execute("DROP INDEX IF EXISTS ux_tags_global_name")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_tags_global_name "
        "ON tags (lower(name)) WHERE scope = 'global'"
    )

    op.execute("ALTER TABLE tags DROP CONSTRAINT IF EXISTS ck_tags_kind_valid")
    op.execute("ALTER TABLE tags DROP COLUMN IF EXISTS kind")
