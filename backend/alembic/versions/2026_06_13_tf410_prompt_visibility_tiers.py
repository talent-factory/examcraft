"""TF-410: prompt visibility/editability tiers + system-institution marker.

Builds the four-tier prompt visibility model (follow-up to TF-346) mirroring
``DocumentVisibility``:

- ``private``      — only the owner (``prompts.user_id``) sees it.
- ``institution``  — every member of the owning institution sees it.
- ``institution`` + ``is_institution_default`` — admin-managed, member-read-only.
- ``system``       — read-only for every institution; lives on the ``is_system``
  institution; only superuser/seed may edit.

Design / constraints (per project conventions):
- Single in-transaction revision, plain DDL/UPDATEs (no CONCURRENTLY).
- Revision id <= 32 chars (alembic_version is VARCHAR(32)).
- ``prompts`` is a premium-only table (created via ``create_all`` only when
  premium is mounted). All prompt DDL/backfill is GUARDED on the table existing,
  so core-only deployments skip it (mirrors tf403_qtype_rename / tf397).
- ``institutions`` / ``users`` / ``user_roles`` / ``roles`` are core tables ->
  always present; the ``is_system`` marker and admin-invariant backfill run
  unconditionally.

Backfill strategy:
1. ``institutions.is_system`` -> mark the lowest-id institution (the existing
   seed convention from TF-346 seed_prompts.py) as the system institution.
2. ``prompts.user_id`` <- ``author_id`` where it is a numeric id of an existing
   user; otherwise NULL (owner-less, editable only by admin/superuser).
3. ``prompts.visibility`` -> system-institution prompts become ``system``; all
   other existing prompts become ``institution`` (preserving the institution-wide
   visibility established in TF-346). New prompts default to ``private``.
4. Admin invariant (TF-410 AC): every non-personal institution must have >=1
   admin. Promote the oldest user of any admin-less non-personal institution to
   the ``admin`` role. Going forward, registration assigns ADMIN to the first
   user of a non-personal institution.

Downgrade drops the columns/types/indexes. It does NOT revert the admin-invariant
backfill (we cannot tell which role grants this migration added, and removing a
legitimate admin would be worse than leaving it).

Revision ID: tf410_prompt_visibility
Revises: tf403_qtype_rename
Create Date: 2026-06-13
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf410_prompt_visibility"
down_revision: Union[str, None] = "tf403_qtype_rename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. System-institution marker (core table -> unconditional).
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE institutions "
        "ADD COLUMN IF NOT EXISTS is_system boolean NOT NULL DEFAULT false"
    )
    # Mark the lowest-id institution as the system institution (matches the
    # pre-TF-410 seed convention). No-op when there are no institutions yet.
    op.execute(
        """
        UPDATE institutions
        SET is_system = true
        WHERE id = (SELECT id FROM institutions ORDER BY id LIMIT 1)
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_institutions_is_system "
        "ON institutions (is_system)"
    )
    # Enforce exactly one system institution.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_institutions_single_system "
        "ON institutions (is_system) WHERE is_system"
    )

    # ------------------------------------------------------------------
    # 2. Prompt visibility tiers (premium-only table -> guarded).
    # ------------------------------------------------------------------
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "prompts" in set(inspector.get_table_names()):
        # Enum type. CREATE TYPE has no IF NOT EXISTS -> guard with a DO block so
        # a re-run (or a type left by a half-applied downgrade) is a no-op.
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'promptvisibility'
                ) THEN
                    CREATE TYPE promptvisibility AS ENUM
                        ('private', 'institution', 'system');
                END IF;
            END$$;
            """
        )

        # Columns. NOT NULL + server default backfills existing rows to 'private'
        # / false; the visibility backfill below then lifts them to their TF-346
        # institution-wide visibility.
        op.execute(
            "ALTER TABLE prompts "
            "ADD COLUMN IF NOT EXISTS visibility promptvisibility "
            "NOT NULL DEFAULT 'private'"
        )
        op.execute(
            "ALTER TABLE prompts "
            "ADD COLUMN IF NOT EXISTS is_institution_default boolean "
            "NOT NULL DEFAULT false"
        )
        op.execute("ALTER TABLE prompts ADD COLUMN IF NOT EXISTS user_id integer")

        # Owner FK: ON DELETE SET NULL -> a deleted user leaves an owner-less
        # prompt rather than cascading the prompt away.
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_prompts_user'
                ) THEN
                    ALTER TABLE prompts
                    ADD CONSTRAINT fk_prompts_user
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
            """
        )

        # Institution-default only valid for institution-visible prompts.
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname =
                      'ck_prompts_institution_default_requires_institution_visibility'
                ) THEN
                    ALTER TABLE prompts
                    ADD CONSTRAINT
                      ck_prompts_institution_default_requires_institution_visibility
                    CHECK (is_institution_default = false
                           OR visibility = 'institution');
                END IF;
            END $$;
            """
        )

        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_prompts_visibility ON prompts (visibility)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_prompts_is_institution_default "
            "ON prompts (is_institution_default)"
        )
        op.execute("CREATE INDEX IF NOT EXISTS ix_prompts_user_id ON prompts (user_id)")

        # Backfill owner from numeric author_id where it resolves to a user.
        op.execute(
            """
            UPDATE prompts p
            SET user_id = p.author_id::integer
            WHERE p.user_id IS NULL
              AND p.author_id ~ '^[0-9]+$'
              AND EXISTS (SELECT 1 FROM users u WHERE u.id = p.author_id::integer)
            """
        )

        # Backfill visibility: preserve TF-346 institution-wide visibility for
        # existing prompts; system-institution prompts become system-visible.
        op.execute(
            """
            UPDATE prompts
            SET visibility = 'institution'
            WHERE institution_id NOT IN
                (SELECT id FROM institutions WHERE is_system)
            """
        )
        op.execute(
            """
            UPDATE prompts
            SET visibility = 'system'
            WHERE institution_id IN
                (SELECT id FROM institutions WHERE is_system)
            """
        )

    # ------------------------------------------------------------------
    # 3. Admin invariant (core tables -> unconditional).
    #    Promote the oldest user of every admin-less non-personal institution to
    #    the 'admin' role. Personal institutions (slug '*-personal') and the
    #    shared 'default-institution' fallback bucket are exempt.
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        DECLARE
            admin_role_id integer;
        BEGIN
            SELECT id INTO admin_role_id FROM roles WHERE name = 'admin' LIMIT 1;
            IF admin_role_id IS NULL THEN
                RAISE NOTICE
                    'admin role missing -> skipping admin-invariant backfill';
                RETURN;
            END IF;

            INSERT INTO user_roles (user_id, role_id)
            SELECT DISTINCT ON (u.institution_id) u.id, admin_role_id
            FROM users u
            JOIN institutions i ON i.id = u.institution_id
            WHERE i.slug NOT LIKE '%-personal'
              AND i.slug <> 'default-institution'
              AND NOT EXISTS (
                  SELECT 1
                  FROM user_roles ur
                  JOIN roles r ON r.id = ur.role_id
                  JOIN users u2 ON u2.id = ur.user_id
                  WHERE u2.institution_id = u.institution_id
                    AND r.name = 'admin'
              )
            ORDER BY u.institution_id, u.id ASC
            ON CONFLICT (user_id, role_id) DO NOTHING;
        END $$;
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "prompts" in set(inspector.get_table_names()):
        op.execute(
            "ALTER TABLE prompts DROP CONSTRAINT IF EXISTS "
            "ck_prompts_institution_default_requires_institution_visibility"
        )
        op.execute("ALTER TABLE prompts DROP CONSTRAINT IF EXISTS fk_prompts_user")
        op.execute("DROP INDEX IF EXISTS ix_prompts_user_id")
        op.execute("DROP INDEX IF EXISTS ix_prompts_is_institution_default")
        op.execute("DROP INDEX IF EXISTS ix_prompts_visibility")
        op.execute("ALTER TABLE prompts DROP COLUMN IF EXISTS user_id")
        op.execute("ALTER TABLE prompts DROP COLUMN IF EXISTS is_institution_default")
        op.execute("ALTER TABLE prompts DROP COLUMN IF EXISTS visibility")
        op.execute("DROP TYPE IF EXISTS promptvisibility")

    op.execute("DROP INDEX IF EXISTS uq_institutions_single_system")
    op.execute("DROP INDEX IF EXISTS ix_institutions_is_system")
    op.execute("ALTER TABLE institutions DROP COLUMN IF EXISTS is_system")
    # Admin-invariant grants are intentionally NOT reverted (see module docstring).
