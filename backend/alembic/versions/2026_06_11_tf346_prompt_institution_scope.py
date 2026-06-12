"""TF-346: scope prompt visibility to the owning institution.

Adds ``prompts.institution_id`` (FK → ``institutions.id``, NOT NULL) so the
Prompt Library can be filtered per institution (Stufe 2 of the 3-tier scoping
model). Visibility filtering itself lives in the API/service layer; this
migration only provides and backfills the column.

Backfill strategy (no orphans — acceptance criterion):
1. Map each existing prompt to its creator's institution via
   ``prompts.author_id`` (a string holding the creator's integer user id) →
   ``users.id`` → ``users.institution_id``.
2. Any prompt whose creator cannot be resolved (null / non-numeric author_id, or
   a user that no longer exists) is assigned to the **system institution**: the
   lowest-id institution.

Also replaces the global unique on ``prompts.name`` with a per-institution
unique index ``(institution_id, lower(name))`` — two institutions may now use
the same prompt name.

Premium-only: the ``prompts`` table is created by ``create_all`` when the
premium package is loaded, not by a migration. Core-only deployments never have
the table, so every step is guarded on its existence. This migration only ever
runs on existing databases (fresh databases are built from the models and
stamped at head — see ``database._run_migrations_or_create_all``). All steps are
idempotent (IF [NOT] EXISTS / catalog guards) and additive — safe for
``AUTO_MIGRATE=true`` deploys. Plain ``CREATE INDEX`` (no ``CONCURRENTLY``) so it
runs inside the migration transaction.

Revision ID: tf346_prompt_institution
Revises: tf399_doc_personal_tags
Create Date: 2026-06-11
"""

from typing import Union

from alembic import op
from sqlalchemy import inspect


revision: str = "tf346_prompt_institution"
down_revision: Union[str, None] = "tf399_doc_personal_tags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "prompts" not in inspector.get_table_names():
        # Core-only deployment: no Prompt Library, nothing to migrate.
        return

    # 1. Add the column as nullable first so existing rows can be backfilled.
    op.execute("ALTER TABLE prompts ADD COLUMN IF NOT EXISTS institution_id INTEGER")

    # 2. Backfill from the creator's institution. author_id is a string holding
    #    the creator's integer user id (or NULL / arbitrary text).
    op.execute(
        """
        UPDATE prompts p
        SET institution_id = u.institution_id
        FROM users u
        WHERE p.institution_id IS NULL
          AND p.author_id ~ '^[0-9]+$'
          AND u.id = p.author_id::bigint
        """
    )

    # 3. Fallback for unresolved prompts → the system (lowest-id) institution.
    op.execute(
        """
        UPDATE prompts
        SET institution_id = (SELECT id FROM institutions ORDER BY id LIMIT 1)
        WHERE institution_id IS NULL
        """
    )

    # 4. Enforce NOT NULL now that every row has a value. If any row is still
    #    NULL here (no institutions exist at all), this fails loudly — which is
    #    correct: a prompt cannot exist without an institution.
    op.execute("ALTER TABLE prompts ALTER COLUMN institution_id SET NOT NULL")

    # 5. Foreign key to institutions (cascade-delete with the institution, like
    #    users). Guarded so re-runs are no-ops.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_prompts_institution'
            ) THEN
                ALTER TABLE prompts
                ADD CONSTRAINT fk_prompts_institution
                FOREIGN KEY (institution_id) REFERENCES institutions(id)
                ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )

    # 6. Index for the per-institution filter path.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prompts_institution_id "
        "ON prompts (institution_id)"
    )

    # 7. Replace the global unique on name with a per-institution unique index
    #    (case-insensitive). The global constraint comes from create_all's
    #    ``unique=True`` (PG default name ``prompts_name_key``).
    op.execute("ALTER TABLE prompts DROP CONSTRAINT IF EXISTS prompts_name_key")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_prompts_institution_name "
        "ON prompts (institution_id, lower(name))"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "prompts" not in inspector.get_table_names():
        return

    # Restore the global unique on name (best-effort — duplicates created across
    # institutions while this migration was applied would make this fail).
    op.execute("DROP INDEX IF EXISTS ux_prompts_institution_name")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'prompts_name_key'
            ) THEN
                ALTER TABLE prompts
                ADD CONSTRAINT prompts_name_key UNIQUE (name);
            END IF;
        END $$;
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_prompts_institution_id")
    op.execute("ALTER TABLE prompts DROP CONSTRAINT IF EXISTS fk_prompts_institution")
    op.execute("ALTER TABLE prompts DROP COLUMN IF EXISTS institution_id")
