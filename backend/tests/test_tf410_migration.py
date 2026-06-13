"""TF-410 migration test — verify the prompt-visibility backfills against real Postgres.

The migration (``2026_06_13_tf410_prompt_visibility_tiers.py``) runs in production
via AUTO_MIGRATE=true and performs four independent backfills, each able to
silently corrupt tenant data if the SQL is wrong:

1. ``prompts.user_id`` <- numeric ``author_id`` that resolves to a real user;
   non-numeric / dangling ids leave ``user_id`` NULL (owner-less prompt).
2. ``prompts.visibility`` -> ``system`` for system-institution prompts, otherwise
   ``institution`` (preserving the TF-346 institution-wide visibility).
3. ``institutions.is_system`` marked on exactly one institution, enforced by a
   partial unique index ``uq_institutions_single_system ... WHERE is_system``.
4. Admin invariant: the oldest user of every admin-less *non-personal*,
   *non-default* institution is promoted to the ``admin`` role.

CI's conftest builds the schema via ``create_all`` and never runs the real
Alembic path, so — like ``test_tf403_migration`` — this exercises the migration's
SQL directly against the transaction-isolated ``test_db``. The DDL (ADD COLUMN /
CREATE TYPE) already exists in the create_all schema; what needs proving is the
data logic, which is what this file asserts.

The prompt backfills are premium-only (``prompts`` is created only when premium
is mounted) and skip cleanly in the core schema, mirroring the migration's own
table guard. The ``is_system`` index and admin-invariant tests use core tables
only and always run.
"""

import importlib.util
import uuid
from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# Statements kept inline (Alembic's op.execute is bound to the migration runtime).
# These mirror core/backend/alembic/versions/2026_06_13_tf410_prompt_visibility_tiers.py.
_TF410_OWNER_BACKFILL_SQL = """
    UPDATE prompts p
    SET user_id = p.author_id::integer
    WHERE p.user_id IS NULL
      AND p.author_id ~ '^[0-9]+$'
      AND EXISTS (SELECT 1 FROM users u WHERE u.id = p.author_id::integer)
"""
_TF410_VIS_INSTITUTION_SQL = """
    UPDATE prompts
    SET visibility = 'institution'
    WHERE institution_id NOT IN (SELECT id FROM institutions WHERE is_system)
"""
_TF410_VIS_SYSTEM_SQL = """
    UPDATE prompts
    SET visibility = 'system'
    WHERE institution_id IN (SELECT id FROM institutions WHERE is_system)
"""
_TF410_SINGLE_SYSTEM_INDEX_SQL = (
    "CREATE UNIQUE INDEX uq_institutions_single_system "
    "ON institutions (is_system) WHERE is_system"
)
_TF410_ADMIN_INVARIANT_SQL = """
    DO $$
    DECLARE
        admin_role_id integer;
    BEGIN
        SELECT id INTO admin_role_id FROM roles WHERE name = 'admin' LIMIT 1;
        IF admin_role_id IS NULL THEN
            RAISE NOTICE 'admin role missing -> skipping admin-invariant backfill';
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


def _institution(test_db, *, slug=None, is_system=False):
    """Create an institution with an autoincrement id (no hardcoded PKs — the CI
    DB is shared and the test transaction rolls back, so ids must not collide)."""
    from models.auth import Institution

    inst = Institution(
        name=f"TF410 {uuid.uuid4().hex[:8]}",
        slug=slug or f"tf410-{uuid.uuid4().hex[:8]}",
        is_system=is_system,
    )
    test_db.add(inst)
    test_db.flush()
    return inst


def _user(test_db, institution):
    from models.auth import User

    user = User(
        email=f"tf410-{uuid.uuid4().hex[:8]}@example.test",
        first_name="TF410",
        last_name="Test",
        institution_id=institution.id,
    )
    test_db.add(user)
    test_db.flush()
    return user


def _admin_role(test_db):
    from models.auth import Role

    role = test_db.query(Role).filter(Role.name == "admin").first()
    if role is None:
        role = Role(
            name="admin",
            display_name="Administrator",
            description="Institution admin",
            permissions="[]",
            is_system_role=True,
        )
        test_db.add(role)
        test_db.flush()
    return role


def _insert_prompt(test_db, *, institution_id, author_id=None):
    """Insert a minimal prompt via raw SQL, leaving visibility at its server
    default ('private') — exactly the state existing rows are in right after the
    migration's ADD COLUMN, before the visibility backfill lifts them."""
    pid = str(uuid.uuid4())
    test_db.execute(
        text(
            """
            INSERT INTO prompts (id, name, content, category, version,
                                 institution_id, author_id)
            VALUES (CAST(:id AS uuid), :name, :content, :category, 1,
                    :institution_id, :author_id)
            """
        ),
        {
            "id": pid,
            "name": f"tf410-prompt-{pid}",
            "content": "x",
            "category": "system_prompt",
            "institution_id": institution_id,
            "author_id": author_id,
        },
    )
    test_db.flush()
    return pid


def _prompt_field(test_db, pid, field):
    row = test_db.execute(
        text(f"SELECT {field} FROM prompts WHERE id = CAST(:id AS uuid)"),
        {"id": pid},
    ).fetchone()
    return row[0] if row is not None else None


def _has_admin(test_db, user_id):
    row = test_db.execute(
        text(
            """
            SELECT 1 FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = :uid AND r.name = 'admin'
            """
        ),
        {"uid": user_id},
    ).fetchone()
    return row is not None


_PROMPTS_REQUIRED = "prompts is premium-only; absent in the core schema"


def _skip_without_prompts(test_db):
    if "prompts" not in set(sa_inspect(test_db.get_bind()).get_table_names()):
        pytest.skip(_PROMPTS_REQUIRED)


# --------------------------------------------------------------------------- #
# Visibility backfill (premium-only)
# --------------------------------------------------------------------------- #
def test_visibility_backfill_system_vs_institution(test_db):
    _skip_without_prompts(test_db)
    system_inst = _institution(test_db, is_system=True)
    normal_inst = _institution(test_db, is_system=False)
    sys_prompt = _insert_prompt(test_db, institution_id=system_inst.id)
    inst_prompt = _insert_prompt(test_db, institution_id=normal_inst.id)

    # Pre-backfill both sit at the server default.
    assert _prompt_field(test_db, sys_prompt, "visibility") == "private"

    test_db.execute(text(_TF410_VIS_INSTITUTION_SQL))
    test_db.execute(text(_TF410_VIS_SYSTEM_SQL))
    test_db.flush()

    assert _prompt_field(test_db, sys_prompt, "visibility") == "system"
    assert _prompt_field(test_db, inst_prompt, "visibility") == "institution"


# --------------------------------------------------------------------------- #
# Owner backfill (premium-only)
# --------------------------------------------------------------------------- #
def test_owner_backfill_numeric_resolves_garbage_and_dangling_null(test_db):
    _skip_without_prompts(test_db)
    inst = _institution(test_db)
    user = _user(test_db, inst)

    resolves = _insert_prompt(test_db, institution_id=inst.id, author_id=str(user.id))
    garbage = _insert_prompt(test_db, institution_id=inst.id, author_id="not-a-number")
    dangling = _insert_prompt(
        test_db,
        institution_id=inst.id,
        author_id="2147483600",  # no such user id
    )

    test_db.execute(text(_TF410_OWNER_BACKFILL_SQL))
    test_db.flush()

    assert _prompt_field(test_db, resolves, "user_id") == user.id
    assert _prompt_field(test_db, garbage, "user_id") is None
    assert _prompt_field(test_db, dangling, "user_id") is None


# --------------------------------------------------------------------------- #
# Single system-institution partial unique index (core)
# --------------------------------------------------------------------------- #
def test_single_system_unique_index_rejects_a_second_system_institution(test_db):
    # Start from a clean slate inside the rolled-back transaction so the index
    # can be created without tripping over fixture rows.
    test_db.execute(text("UPDATE institutions SET is_system = false"))
    test_db.execute(text(_TF410_SINGLE_SYSTEM_INDEX_SQL))
    test_db.flush()

    _institution(test_db, is_system=True)  # first system institution: OK
    with pytest.raises(IntegrityError):
        with test_db.begin_nested():
            _institution(test_db, is_system=True)  # second: violates partial unique


# --------------------------------------------------------------------------- #
# Admin invariant (core)
# --------------------------------------------------------------------------- #
def test_admin_invariant_promotes_oldest_user_of_non_personal_institution(test_db):
    _admin_role(test_db)
    inst = _institution(test_db, slug=f"tf410-org-{uuid.uuid4().hex[:8]}")
    oldest = _user(test_db, inst)  # inserted first -> lowest id -> "oldest"
    newer = _user(test_db, inst)

    test_db.execute(text(_TF410_ADMIN_INVARIANT_SQL))
    test_db.flush()

    assert _has_admin(test_db, oldest.id) is True
    assert _has_admin(test_db, newer.id) is False


def test_admin_invariant_exempts_personal_and_default_institutions(test_db):
    _admin_role(test_db)
    personal = _institution(test_db, slug=f"user-{uuid.uuid4().hex[:8]}-personal")
    default = _institution(test_db, slug="default-institution")
    personal_user = _user(test_db, personal)
    default_user = _user(test_db, default)

    test_db.execute(text(_TF410_ADMIN_INVARIANT_SQL))
    test_db.flush()

    assert _has_admin(test_db, personal_user.id) is False
    assert _has_admin(test_db, default_user.id) is False


def test_admin_invariant_skips_institution_that_already_has_an_admin(test_db):
    admin_role = _admin_role(test_db)
    inst = _institution(test_db, slug=f"tf410-org-{uuid.uuid4().hex[:8]}")
    existing_admin = _user(test_db, inst)
    other = _user(test_db, inst)
    # Pre-grant admin to the *second* user; the invariant must then touch nobody.
    test_db.execute(
        text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
        {"u": other.id, "r": admin_role.id},
    )
    test_db.flush()

    test_db.execute(text(_TF410_ADMIN_INVARIANT_SQL))
    test_db.flush()

    # The pre-existing admin stays; the oldest user is NOT additionally promoted.
    assert _has_admin(test_db, other.id) is True
    assert _has_admin(test_db, existing_admin.id) is False


# --------------------------------------------------------------------------- #
# Revision chain / id limit (core)
# --------------------------------------------------------------------------- #
def test_migration_revision_chain_and_id_limit():
    """alembic_version.version_num is VARCHAR(32) so the revision id must fit,
    and down_revision must chain onto the develop head it branched from."""
    mig_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "2026_06_13_tf410_prompt_visibility_tiers.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tf410_prompt_visibility_mig", mig_path
    )
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    assert len(mig.revision) <= 32
    assert mig.revision == "tf410_prompt_visibility"
    assert mig.down_revision == "tf403_qtype_rename"
