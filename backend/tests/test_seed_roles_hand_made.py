"""EXAMCRAFT-150: Der Rollen-Seed füllt handgemachte Rollen nicht auf.

Eine Rolle mit dem Namen einer Seed-Systemrolle (admin, dozent, assistant,
viewer), die kein ``is_system_role`` trägt, stammt aus der Admin-API. Der Seed
lässt sie unverändert; echte Systemrollen behalten das Set-Merge-Verhalten.
"""

from unittest.mock import MagicMock

import pytest

from models.auth import Role
from utils import seed_roles
from utils.permissions import parse_role_permissions

_SYSTEM_NAMES = ("admin", "dozent", "assistant", "viewer")


@pytest.fixture(autouse=True)
def _clean_roles(test_db):
    """Die Rollen können aus dem App-Start-Seed schon in der geteilten DB liegen."""
    test_db.query(Role).filter(Role.name.in_((*_SYSTEM_NAMES, "mcp_user"))).delete(
        synchronize_session=False
    )
    test_db.flush()
    yield
    test_db.rollback()


def _role(test_db, name):
    return test_db.query(Role).filter(Role.name == name).one()


@pytest.mark.parametrize(
    "stored",
    ['["view_questions"]', "[]", "{view_questions}"],
    ids=["json", "leer", "legacy-set"],
)
def test_handgemachte_rolle_bleibt_unveraendert(test_db, monkeypatch, stored):
    test_db.add(
        Role(
            name="admin",
            display_name="eingeschränkt",
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

    role = _role(test_db, "admin")
    assert role.permissions == stored
    assert role.display_name == "eingeschränkt"
    assert role.description == "von Hand"
    assert role.is_system_role is False
    assert log.warning.called
    # Die übrigen Rollen werden trotzdem geseedet (continue statt return) ...
    for name in ("dozent", "assistant", "viewer", "mcp_user"):
        assert test_db.query(Role).filter(Role.name == name).count() == 1
    # ... und die übersprungene Rolle zählt weder als angelegt noch aktualisiert.
    assert created == 4
    assert updated == 0


def test_zweiter_lauf_aendert_handgemachte_rolle_weiter_nicht(test_db):
    test_db.add(
        Role(
            name="admin",
            display_name="eingeschränkt",
            permissions='["view_questions"]',
            is_system_role=False,
        )
    )
    test_db.flush()

    seed_roles.seed_default_roles(test_db)
    seed_roles.seed_default_roles(test_db)
    test_db.expire_all()

    role = _role(test_db, "admin")
    assert role.permissions == '["view_questions"]'
    assert role.is_system_role is False


def test_systemrolle_behaelt_set_merge(test_db):
    test_db.add(
        Role(
            name="viewer",
            display_name="alt",
            permissions='["view_questions", "extra:admin"]',
            is_system_role=True,
        )
    )
    test_db.flush()

    seed_roles.seed_default_roles(test_db)
    test_db.expire_all()

    role = _role(test_db, "viewer")
    perms = set(parse_role_permissions(role.permissions))
    assert {"view_questions", "view_exams", "prompt:read", "extra:admin"} <= perms
    assert role.display_name == "Viewer"
    assert role.is_system_role is True


def test_systemrolle_im_legacy_format_wird_gemergt(test_db):
    test_db.add(
        Role(
            name="assistant",
            display_name="alt",
            permissions="{edit_questions,view_questions}",
            is_system_role=True,
        )
    )
    test_db.flush()

    seed_roles.seed_default_roles(test_db)
    test_db.expire_all()

    perms = parse_role_permissions(_role(test_db, "assistant").permissions)
    assert "submissions:grade" in perms
    assert "view_questions" in perms


def test_fehlende_systemrollen_werden_angelegt(test_db):
    created, updated = seed_roles.seed_default_roles(test_db)
    test_db.expire_all()

    assert (created, updated) == (5, 0)  # 4 Systemrollen + mcp_user
    for name in _SYSTEM_NAMES:
        assert _role(test_db, name).is_system_role is True
