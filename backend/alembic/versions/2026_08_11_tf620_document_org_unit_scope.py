"""Add ``documents.org_unit_id`` for team-scoped visibility (TF-620, part B).

Adds the column, FK, and invariant that back the ``team`` visibility tier
added in the previous revision (``tf620_doc_vis_team_enum`` — must already be
committed, see that file's docstring for why this is split in two).

Steps:
1. ``documents.org_unit_id`` — nullable ``INTEGER`` FK to ``org_units.id``.
   Nullable because it only applies when ``visibility = 'team'``. No
   ``ON DELETE CASCADE``/``SET NULL``: deleting a document because its
   Org-Unit was deleted would be silent data loss, and ``SET NULL`` would
   silently violate the CHECK constraint added in step 2 (a NULL org_unit_id
   with visibility still 'team'). Default ``NO ACTION`` — deleting a
   referenced Org-Unit is rejected at the DB level;
   ``services/org_unit_service.delete_org_unit`` catches the resulting
   ``IntegrityError`` and surfaces a 409, mirroring the existing
   sibling-name-conflict handling in the same function.
2. CHECK constraint ``ck_documents_team_visibility_requires_org_unit``
   (``(visibility = 'team') = (org_unit_id IS NOT NULL)``) — a full
   biconditional, not just "team requires a value". Unlike the existing
   ``ck_documents_institution_visibility_requires_institution`` (TF-354),
   which is intentionally one-directional because ``institution_id`` is a
   dual-purpose multi-tenancy marker set on every row regardless of
   visibility, ``org_unit_id`` exists solely to scope team visibility, so the
   DB can and should also reject a non-NULL ``org_unit_id`` on any
   non-``team`` row. Safe to add immediately: the ``org_unit_id`` column is
   brand new in this same revision (no existing row has it set), and no row
   can have ``visibility = 'team'`` yet (that value didn't exist before the
   previous revision), so no row can violate either direction.
3. Index ``ix_documents_org_unit_id`` — backs the read-filter join added in
   ``utils/document_visibility.py`` (team-visible rows whose org_unit_id is
   in the viewer's accessible Org-Unit set).

Additive and idempotent (column/index guarded by ``IF NOT EXISTS``,
constraint guarded by a ``pg_constraint`` DO block, matching tf354). Safe for
``AUTO_MIGRATE=true`` deploys.

Revision ID: tf620_doc_org_unit_scope
Revises: tf620_doc_vis_team_enum
"""

from typing import Union

from alembic import op

revision: str = "tf620_doc_org_unit_scope"
down_revision: Union[str, None] = "tf620_doc_vis_team_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Column + FK.
    op.execute(
        "ALTER TABLE documents "
        "ADD COLUMN IF NOT EXISTS org_unit_id INTEGER "
        "REFERENCES org_units(id)"
    )

    # 2. Invariant: a team-visible document must reference an Org-Unit.
    #    Postgres has no ADD CONSTRAINT IF NOT EXISTS, so guard with a DO block.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname =
                    'ck_documents_team_visibility_requires_org_unit'
            ) THEN
                ALTER TABLE documents
                    ADD CONSTRAINT
                        ck_documents_team_visibility_requires_org_unit
                    CHECK (
                        (visibility = 'team') = (org_unit_id IS NOT NULL)
                    );
            END IF;
        END$$;
        """
    )

    # 3. Index for the read-filter join (see module docstring).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_org_unit_id ON documents (org_unit_id)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE documents DROP CONSTRAINT IF EXISTS "
        "ck_documents_team_visibility_requires_org_unit"
    )
    op.execute("DROP INDEX IF EXISTS ix_documents_org_unit_id")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS org_unit_id")
