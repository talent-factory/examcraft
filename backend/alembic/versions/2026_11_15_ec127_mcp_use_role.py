"""initial grant of the permission mcp:use (EXAMCRAFT-127)

The MCP server no longer uses the ``ALLOWED_EMAILS`` whitelist; access is the
opt-in permission ``mcp:use`` (ADR 0008). To keep the current operators
connected, this migration creates the role ``mcp_user`` (permission
``mcp:use``) and assigns it to every user whose e-mail is in ``ALLOWED_EMAILS``
at migration time. Superusers need no role (``has_permission`` is true for
them). Idempotent; without ``ALLOWED_EMAILS`` only the role is created.

Additive: no existing row is changed. Downgrade removes the role; the
``user_roles`` rows go with it (ON DELETE CASCADE).

Revision ID: ec127_mcp_use_role
Revises: ec125_auth_sessions
Create Date: 2026-11-15 18:00:00.000000
"""

import json
import logging
import os
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ec127_mcp_use_role"
down_revision: Union[str, None] = "ec125_auth_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

ROLE_NAME = "mcp_user"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO roles "
            "(name, display_name, description, permissions, is_active, is_system_role) "
            "VALUES (:name, :display_name, :description, :permissions, true, false) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {
            "name": ROLE_NAME,
            "display_name": "MCP-Zugang",
            "description": "Berechtigt zur Nutzung des MCP-Servers (Ops-Tools).",
            "permissions": json.dumps(["mcp:use"]),
        },
    )

    stored = bind.execute(
        sa.text("SELECT permissions FROM roles WHERE name = :name"),
        {"name": ROLE_NAME},
    ).scalar()
    # The column holds a JSON list or, once seed_default_roles rewrote it, a
    # Postgres array literal ({a,b}): compare tokens, not the raw string.
    if "mcp:use" not in re.findall(r"[\w:.\-]+", stored or ""):
        # Role existed before with other permissions: ON CONFLICT left it as is.
        # Do not put users into a foreign role; an operator decides.
        logger.error(
            "Rolle %s existiert ohne mcp:use. Keine Zuweisung aus ALLOWED_EMAILS, "
            "Permissions der Rolle von Hand korrigieren und mcp:use vergeben.",
            ROLE_NAME,
        )
        return

    emails = [
        e.strip().lower()
        for e in os.getenv("ALLOWED_EMAILS", "").split(",")
        if e.strip()
    ]
    if not emails:
        logger.warning(
            "ALLOWED_EMAILS ist leer: mcp:use wird nicht vergeben. Nicht-Superuser "
            "erhalten die Rolle %s von Hand.",
            ROLE_NAME,
        )
        return

    result = bind.execute(
        sa.text(
            "INSERT INTO user_roles (user_id, role_id) "
            "SELECT u.id, r.id FROM users u CROSS JOIN roles r "
            "WHERE r.name = :role AND lower(u.email) IN :emails "
            "ON CONFLICT DO NOTHING"
        ).bindparams(sa.bindparam("emails", expanding=True)),
        {"role": ROLE_NAME, "emails": emails},
    )
    logger.info(
        "mcp:use vergeben an %s von %s Adressen aus ALLOWED_EMAILS.",
        result.rowcount,
        len(emails),
    )
    existing = {
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT lower(email) FROM users WHERE lower(email) IN :emails"
            ).bindparams(sa.bindparam("emails", expanding=True)),
            {"emails": emails},
        )
    }
    unmatched = sorted(set(emails) - existing)
    if unmatched:
        logger.warning(
            "%s Adresse(n) aus ALLOWED_EMAILS ohne Benutzerkonto, kein mcp:use "
            "(Adressen bewusst nicht geloggt, ALLOWED_EMAILS prüfen).",
            len(unmatched),
        )


def downgrade() -> None:
    # Only the role this migration created: a hand-made role of the same name
    # (other permissions) must not be deleted, its user_roles go with CASCADE.
    op.get_bind().execute(
        sa.text(
            "DELETE FROM roles WHERE name = :name "
            "AND permissions IN (:json_format, :array_format) "
            "AND is_system_role = false"
        ),
        {
            "name": ROLE_NAME,
            "json_format": json.dumps(["mcp:use"]),
            # seed_default_roles rewrites the column as a Postgres array literal
            "array_format": "{mcp:use}",
        },
    )
