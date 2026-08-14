"""Add ``team`` value to the ``promptvisibility`` enum (TF-641, part A).

TF-641 introduces a third prompt-visibility tier between ``private`` and
``institution``: scoping a prompt to a single Org-Unit (department/team),
mirroring ``DocumentVisibility.TEAM`` (TF-620).

This is a **separate, minimal revision** on purpose — same reasoning as
``tf620_doc_vis_team_enum``: Postgres refuses to use a newly added enum value
within a transaction that is still open when the value was added, and
Alembic's ``env.py`` runs all pending revisions of one ``alembic upgrade``
invocation inside a single ambient transaction, not one per revision. The fix
is ``MigrationContext.autocommit_block()``, which suspends the ambient
transaction, runs the ``ALTER TYPE`` in its own committed transaction, and
correctly restores Alembic's transaction bookkeeping afterwards. The
column/constraint/index that reference ``'team'`` live in the next revision
(``tf641_prompt_org_unit_scope``), so they only run once the enum value from
this autocommit block has definitely landed.

``ADD VALUE IF NOT EXISTS`` is native syntax since Postgres 9.6 (project
targets Postgres 17).

Additive and idempotent, safe for ``AUTO_MIGRATE=true``.

Revision ID: tf641_prompt_vis_team_enum
Revises: tf637_org_unit_role
"""

from typing import Union

from alembic import op

revision: str = "tf641_prompt_vis_team_enum"
down_revision: Union[str, None] = "tf637_org_unit_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE promptvisibility ADD VALUE IF NOT EXISTS 'team'")


def downgrade() -> None:
    # Postgres cannot drop a single enum value. A real downgrade would need to
    # rebuild the type (rename old -> create new without 'team' -> cast column
    # -> drop old), which is only safe if no row uses 'team' — the next
    # revision's downgrade already clears the column/constraint that would
    # reference it, and enforces (via its own downgrade order) that this runs
    # first. Left as a no-op: an unused enum label is harmless, and forcing a
    # type rebuild here would risk data loss if a caller downgrades out of
    # order with rows still present.
    pass
