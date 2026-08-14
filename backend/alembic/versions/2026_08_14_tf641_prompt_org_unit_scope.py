"""Add ``prompts.org_unit_id`` for team-scoped visibility (TF-641).

Adds the column, FK, and invariant that back the ``team`` visibility tier
added in the previous revision (``tf641_prompt_vis_team_enum`` — must already
be committed, see that file's docstring for why this is split in two).
Mirrors ``tf620_doc_org_unit_scope`` (the ``documents.org_unit_id`` sibling).

Steps:
1. ``prompts.org_unit_id`` — nullable ``INTEGER`` FK to ``org_units.id``.
   Nullable because it only applies when ``visibility = 'team'``. No
   ``ON DELETE CASCADE``/``SET NULL``: deleting a prompt because its Org-Unit
   was deleted would be silent data loss, and ``SET NULL`` would silently
   violate the CHECK constraint added in step 2 (a NULL org_unit_id with
   visibility still 'team'). Default ``NO ACTION`` — deleting a referenced
   Org-Unit is rejected at the DB level;
   ``services/org_unit_service.delete_org_unit`` catches the resulting
   ``IntegrityError`` and surfaces a 409, mirroring the existing
   sibling-name-conflict handling in the same function.
2. CHECK constraint ``ck_prompts_team_visibility_requires_org_unit``
   (``(visibility = 'team') = (org_unit_id IS NOT NULL)``) — a full
   biconditional. ``org_unit_id`` exists solely to scope team visibility, so
   the DB can and should also reject a non-NULL ``org_unit_id`` on any
   non-``team`` row. Safe to add immediately: the ``org_unit_id`` column is
   brand new in this same revision (no existing row has it set), and no row
   can have ``visibility = 'team'`` yet (that value didn't exist before the
   previous revision), so no row can violate either direction.
3. Index ``ix_prompts_org_unit_id`` — backs the read-filter join added in
   ``services/prompt_service.py`` (team-visible rows whose org_unit_id is in
   the viewer's accessible Org-Unit set).

Note: ``is_institution_default`` stays exclusively bound to
``visibility = 'institution'`` (existing constraint
``ck_prompts_institution_default_requires_institution_visibility``, TF-410) —
a team-scoped prompt can never be an institution default. TF-641 deliberately
did not touch that constraint.

Additive and idempotent (column/index guarded by ``IF NOT EXISTS``,
constraint guarded by a ``pg_constraint`` DO block, matching tf620). Safe for
``AUTO_MIGRATE=true`` deploys.

Revision ID: tf641_prompt_org_unit_scope
Revises: tf641_prompt_vis_team_enum
"""

from typing import Union

from alembic import op

revision: str = "tf641_prompt_org_unit_scope"
down_revision: Union[str, None] = "tf641_prompt_vis_team_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Column + FK.
    op.execute(
        "ALTER TABLE prompts "
        "ADD COLUMN IF NOT EXISTS org_unit_id INTEGER "
        "REFERENCES org_units(id)"
    )

    # 2. Invariant: a team-visible prompt must reference an Org-Unit.
    #    Postgres has no ADD CONSTRAINT IF NOT EXISTS, so guard with a DO block.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname =
                    'ck_prompts_team_visibility_requires_org_unit'
            ) THEN
                ALTER TABLE prompts
                    ADD CONSTRAINT
                        ck_prompts_team_visibility_requires_org_unit
                    CHECK (
                        (visibility = 'team') = (org_unit_id IS NOT NULL)
                    );
            END IF;
        END$$;
        """
    )

    # 3. Index for the read-filter join (see module docstring).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prompts_org_unit_id ON prompts (org_unit_id)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE prompts DROP CONSTRAINT IF EXISTS "
        "ck_prompts_team_visibility_requires_org_unit"
    )
    op.execute("DROP INDEX IF EXISTS ix_prompts_org_unit_id")
    op.execute("ALTER TABLE prompts DROP COLUMN IF EXISTS org_unit_id")
