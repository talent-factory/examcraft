"""EXAMCRAFT-127: Migration ``ec127_mcp_use_role`` (Rolle ``mcp_user``).

Die Migration läuft in Prod nur auf einer bestehenden DB (frische DBs: create_all
+ stamp head). Deshalb wird ``upgrade()``/``downgrade()`` hier direkt gegen die
Test-DB ausgeführt, mit einer Alembic-``Operations``-Umgebung.
"""

import importlib.util
from unittest.mock import MagicMock
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

from models.auth import Institution, Role, User
from utils.permissions import parse_role_permissions

_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "2026_11_15_ec127_mcp_use_role.py"
)


@pytest.fixture(scope="module")
def migration():
    spec = importlib.util.spec_from_file_location("ec127_mcp_use_role", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _clean_mcp_role(test_db):
    """Die Rolle kann aus dem App-Start-Seed schon in der geteilten DB liegen."""
    test_db.query(Role).filter(Role.name == "mcp_user").delete()
    test_db.flush()
    yield
    test_db.rollback()
    test_db.query(Role).filter(Role.name == "mcp_user").delete()
    test_db.commit()


def _run(test_db, fn):
    test_db.flush()
    ctx = MigrationContext.configure(test_db.connection())
    with Operations.context(ctx):
        fn()
    test_db.expire_all()


def _user(test_db, email):
    slug = f"mig-{uuid.uuid4().hex[:8]}"
    inst = Institution(
        name=slug,
        slug=slug,
        domain=f"{slug}.example.com",
        subscription_tier="free",
        max_users=100,
        max_documents=50,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    user = User(
        email=email,
        first_name="M",
        last_name="C",
        institution_id=inst.id,
        status="active",
        is_superuser=False,
    )
    test_db.add(user)
    test_db.flush()
    return user


def _mcp_role(test_db):
    return test_db.query(Role).filter(Role.name == "mcp_user").one_or_none()


def test_upgrade_vergibt_rolle_nur_an_passende_adressen(
    test_db, migration, monkeypatch
):
    tag = uuid.uuid4().hex[:6]
    allowed = _user(test_db, f"Dozent-{tag}@Example.com")
    other = _user(test_db, f"other-{tag}@example.com")
    monkeypatch.setenv(
        "ALLOWED_EMAILS", f" dozent-{tag}@example.com , unbekannt-{tag}@example.com ,"
    )

    _run(test_db, migration.upgrade)

    role = _mcp_role(test_db)
    assert role is not None and role.is_system_role is False
    assert parse_role_permissions(role.permissions) == ["mcp:use"]
    # Gelesen über das echte Permission-Format der App.
    assert allowed.has_permission("mcp:use") is True
    assert other.has_permission("mcp:use") is False


def test_upgrade_ist_idempotent_und_loggt_keine_adressen(
    test_db, migration, monkeypatch
):
    tag = uuid.uuid4().hex[:6]
    user = _user(test_db, f"idem-{tag}@example.com")
    monkeypatch.setenv(
        "ALLOWED_EMAILS", f"idem-{tag}@example.com,geheim-{tag}@example.com"
    )

    log = MagicMock()
    monkeypatch.setattr(migration, "logger", log)
    _run(test_db, migration.upgrade)
    _run(test_db, migration.upgrade)

    assert test_db.query(Role).filter(Role.name == "mcp_user").count() == 1
    assert len(user.roles) == 1
    # Positive proof that the logger was reached, then: no address in any record.
    assert log.info.called and log.warning.called
    rendered = " ".join(
        str(a) for call in log.method_calls for a in call.args[1:]
    ) + " ".join(str(call.args[0]) for call in log.method_calls)
    assert f"geheim-{tag}" not in rendered
    assert f"idem-{tag}" not in rendered


def test_upgrade_ohne_allowed_emails_legt_nur_die_rolle_an(
    test_db, migration, monkeypatch
):
    user = _user(test_db, f"none-{uuid.uuid4().hex[:6]}@example.com")
    monkeypatch.setenv("ALLOWED_EMAILS", "")

    _run(test_db, migration.upgrade)

    assert _mcp_role(test_db) is not None
    assert user.has_permission("mcp:use") is False


def test_upgrade_vorhandene_rolle_ohne_mcp_use_wird_nicht_zugewiesen(
    test_db, migration, monkeypatch
):
    test_db.add(Role(name="mcp_user", display_name="alt", permissions='["x:y"]'))
    user = _user(test_db, f"foreign-{uuid.uuid4().hex[:6]}@example.com")
    test_db.flush()
    monkeypatch.setenv("ALLOWED_EMAILS", user.email)
    log = MagicMock()
    monkeypatch.setattr(migration, "logger", log)

    _run(test_db, migration.upgrade)

    assert log.error.called
    assert user.roles == []


def test_downgrade_loescht_auch_vom_seed_umgeschriebene_rolle(
    test_db, migration, monkeypatch
):
    """seed_default_roles rewrites the column as a Postgres array literal."""
    from utils.seed_roles import seed_default_roles

    monkeypatch.setenv("ALLOWED_EMAILS", "")
    _run(test_db, migration.upgrade)
    seed_default_roles(test_db)  # merges permissions -> {mcp:use}
    test_db.expire_all()

    _run(test_db, migration.downgrade)

    assert _mcp_role(test_db) is None


def test_downgrade_laesst_systemrolle_gleichen_namens_stehen(
    test_db, migration, monkeypatch
):
    test_db.add(
        Role(
            name="mcp_user",
            display_name="sys",
            permissions='["mcp:use"]',
            is_system_role=True,
        )
    )
    test_db.flush()
    _run(test_db, migration.downgrade)
    assert _mcp_role(test_db) is not None


def test_downgrade_entfernt_user_roles_per_cascade(test_db, migration, monkeypatch):
    user = _user(test_db, f"casc-{uuid.uuid4().hex[:6]}@example.com")
    monkeypatch.setenv("ALLOWED_EMAILS", user.email)
    _run(test_db, migration.upgrade)
    assert len(user.roles) == 1

    _run(test_db, migration.downgrade)

    test_db.refresh(user)
    assert user.roles == []


def test_downgrade_loescht_nur_die_eigene_rolle(test_db, migration, monkeypatch):
    monkeypatch.setenv("ALLOWED_EMAILS", "")
    _run(test_db, migration.upgrade)
    _run(test_db, migration.downgrade)
    assert _mcp_role(test_db) is None

    # Von Hand angelegte Rolle gleichen Namens bleibt erhalten.
    test_db.add(Role(name="mcp_user", display_name="manuell", permissions="[]"))
    test_db.flush()
    _run(test_db, migration.downgrade)
    assert _mcp_role(test_db) is not None


def test_seed_default_roles_legt_mcp_user_an(test_db):
    """Frische Instanzen (create_all + stamp) bekommen die Rolle über den Seed."""
    from utils.permissions import role_is_superuser_grant_only
    from utils.seed_roles import seed_default_roles

    seed_default_roles(test_db)
    seed_default_roles(test_db)  # idempotent

    assert test_db.query(Role).filter(Role.name == "mcp_user").count() == 1
    role = _mcp_role(test_db)
    assert parse_role_permissions(role.permissions) == ["mcp:use"]
    assert role_is_superuser_grant_only(role) is True
    for name in ("admin", "dozent", "assistant", "viewer"):
        std = test_db.query(Role).filter(Role.name == name).one()
        assert role_is_superuser_grant_only(std) is False


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ('["view_questions"]', ["view_questions"]),
        ("[]", []),
        ("{view_questions}", ["view_questions"]),
    ],
)
def test_seed_laesst_handgemachte_mcp_user_unveraendert(
    test_db, monkeypatch, stored, expected
):
    """EXAMCRAFT-140: Fremde Rechte bekommen nicht still mcp:use."""
    from utils import seed_roles

    test_db.add(
        Role(
            name="mcp_user",
            display_name="manuell",
            description="von Hand",
            permissions=stored,
            is_system_role=False,
        )
    )
    test_db.flush()
    log = MagicMock()
    monkeypatch.setattr(seed_roles, "logger", log)

    created, updated = seed_roles.seed_default_roles(test_db)
    test_db.expire_all()

    role = _mcp_role(test_db)
    assert parse_role_permissions(role.permissions) == expected
    assert role.display_name == "manuell"
    assert role.description == "von Hand"
    assert log.warning.called
    # Der übersprungene Datensatz zählt weder als angelegt noch als aktualisiert.
    assert created + updated == 4


def test_seed_aktualisiert_unveraenderte_mcp_user_im_legacy_format(
    test_db, monkeypatch
):
    """Ein vom Seed früher umgeschriebenes ``{mcp:use}`` gilt nicht als fremd."""
    from utils import seed_roles

    test_db.add(
        Role(
            name="mcp_user",
            display_name="alt",
            permissions="{mcp:use}",
            is_system_role=False,
        )
    )
    test_db.flush()
    log = MagicMock()
    monkeypatch.setattr(seed_roles, "logger", log)

    seed_roles.seed_default_roles(test_db)
    test_db.expire_all()

    assert _mcp_role(test_db).display_name == "MCP-Zugang"
    assert not log.warning.called


def test_seed_synchronisiert_mcp_user_mit_mcp_use_und_extras(test_db):
    """Hat die Rolle mcp:use schon, vergibt der Seed nichts Neues: Extras bleiben."""
    from utils.seed_roles import seed_default_roles

    test_db.add(
        Role(
            name="mcp_user",
            display_name="alt",
            permissions='["mcp:use", "view_questions"]',
            is_system_role=False,
        )
    )
    test_db.flush()

    seed_default_roles(test_db)
    test_db.expire_all()

    role = _mcp_role(test_db)
    assert role.display_name == "MCP-Zugang"
    assert set(parse_role_permissions(role.permissions)) == {
        "mcp:use",
        "view_questions",
    }
