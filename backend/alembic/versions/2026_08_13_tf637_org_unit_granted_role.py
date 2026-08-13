"""Add ``org_units.role_id`` for the Granted Role RBAC-inheritance pilot (TF-637).

Design: docs/superpowers/specs/2026-08-13-org-unit-rbac-vererbung-design.md

An Org-Unit can optionally grant a *Role* (``models.auth.Role``) to its
*direct* members -- see ``User.has_permission()`` for how this is consumed.
This is deliberately additive and non-cascading (ADR-0003 in
``docs/adr/0003-granted-role-not-cascading.md``): the schema change here is
just the column, no behavioural coupling to the existing Access-Scope
cascade (``get_user_accessible_org_unit_ids``).

``ondelete="SET NULL"``, not ``CASCADE``: the only existing precedent
(``user_roles.role_id``) uses CASCADE, but that's a pure junction table --
deleting a Role would delete the join row, which is correct there. Here
``role_id`` lives directly on ``org_units``; CASCADE would delete the
Org-Unit itself when its Granted Role is removed, which would be silent,
unrelated data loss. SET NULL just clears the grant.

Additive and idempotent (column/index guarded by ``IF NOT EXISTS``), safe
for ``AUTO_MIGRATE=true`` deploys -- matches the tf620/tf354 pattern.

Revision ID: tf637_org_unit_role
Revises: tf620_doc_org_unit_scope
"""

from typing import Union

from alembic import op

revision: str = "tf637_org_unit_role"
down_revision: Union[str, None] = "tf620_doc_org_unit_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE org_units "
        "ADD COLUMN IF NOT EXISTS role_id INTEGER "
        "REFERENCES roles(id) ON DELETE SET NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_org_units_role_id ON org_units (role_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_org_units_role_id")
    op.execute("ALTER TABLE org_units DROP COLUMN IF EXISTS role_id")
