"""Add ``team`` value to the ``documentvisibility`` enum (TF-620, part A).

TF-620 introduces a third document-visibility tier between ``private`` and
``institution``: scoping a document to a single Org-Unit (department/team,
see TF-603-precursor PR #173) so only that Org-Unit's members see it.

This is a **separate, minimal revision** on purpose: Postgres refuses to use
a newly added enum value within a transaction that is still open when the
value was added — and by default Alembic's ``env.py`` (unchanged here) runs
*all* pending revisions of one ``alembic upgrade`` invocation inside a single
ambient transaction, not one per revision, so simply splitting into two
migration *files* is not sufficient on its own (verified against a scratch
DB: batching both revisions' DDL in the ambient transaction raises
``psycopg2.errors.UnsafeNewEnumValueUsage``).

The fix is Alembic's purpose-built escape hatch for exactly this case —
``MigrationContext.autocommit_block()`` — which suspends the ambient
transaction, runs the ``ALTER TYPE`` in its own committed transaction, and
correctly restores Alembic's transaction bookkeeping afterwards (unlike a
raw ``op.execute("COMMIT")``, which desyncs SQLAlchemy's ``Transaction``
object from the underlying DBAPI connection). The column/constraint/index
that reference ``'team'`` still live in the next revision
(``tf620_doc_org_unit_scope``), so they only run once the enum value from
this autocommit block has definitely landed.

``ADD VALUE IF NOT EXISTS`` is native syntax since Postgres 9.6 (project
targets Postgres 17) — no ``pg_enum`` existence guard needed, unlike the
older enum-*type*-creation guard in ``tf354_documents_visibility.py`` (which
predates ``IF NOT EXISTS`` support for ``CREATE TYPE``, still absent today).

Additive and idempotent, safe for ``AUTO_MIGRATE=true``.

Revision ID: tf620_doc_vis_team_enum
Revises: orgunits_foundation
"""

from typing import Union

from alembic import op

revision: str = "tf620_doc_vis_team_enum"
down_revision: Union[str, None] = "orgunits_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE documentvisibility ADD VALUE IF NOT EXISTS 'team'")


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
