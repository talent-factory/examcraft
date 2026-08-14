"""Tests for the Institution-Admin read-all bypass helper (TF-639).

Design: docs/adr/0004-institution-admin-read-all-bypass-convention.md

Each of the five resources (documents, prompts, questions, exams,
competencies) gets its own ``<resource>:read_all`` permission string.
``has_read_all_bypass()`` is the single point every resource's own
visibility filter (the ``document_visibility.py`` pattern) is meant to call
to check it -- wiring the actual query filter into any resource is that
resource's own ticket, not this one. TF-639 only establishes the registry
and this thin helper.
"""

import pytest

from models.auth import Institution, Role, User, UserStatus
from utils.resource_visibility import (
    RESOURCE_READ_ALL_PERMISSIONS,
    has_read_all_bypass,
)


def _make_institution(db, slug: str = "resource-visibility-test") -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _make_user(db, inst: Institution, email: str, is_superuser: bool = False) -> User:
    user = User(
        email=email,
        institution_id=inst.id,
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()
    return user


def _make_role(db, name: str, permissions: list[str]) -> Role:
    role = Role(name=name, display_name=name, permissions=permissions, is_active=True)
    db.add(role)
    db.flush()
    return role


def test_registry_maps_all_five_resources_to_their_permission_string():
    assert dict(RESOURCE_READ_ALL_PERMISSIONS) == {
        "documents": "documents:read_all",
        "prompts": "prompt:read_all",
        "questions": "questions:read_all",
        "exams": "exams:read_all",
        "competencies": "competencies:read_all",
    }


def test_superuser_bypasses_every_resource(test_db):
    inst = _make_institution(test_db)
    user = _make_user(
        test_db, inst, "super@resource-visibility-test.example", is_superuser=True
    )

    for resource in RESOURCE_READ_ALL_PERMISSIONS:
        assert has_read_all_bypass(user, resource) is True


def test_user_with_matching_permission_bypasses(test_db):
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst, "admin@resource-visibility-test.example")
    role = _make_role(test_db, "docs-admin", ["documents:read_all"])
    user.roles.append(role)
    test_db.commit()
    test_db.refresh(user)

    assert has_read_all_bypass(user, "documents") is True


def test_user_without_permission_does_not_bypass(test_db):
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst, "plain@resource-visibility-test.example")
    role = _make_role(test_db, "dozent-role", ["create_questions"])
    user.roles.append(role)
    test_db.commit()
    test_db.refresh(user)

    assert has_read_all_bypass(user, "documents") is False


def test_permission_is_scoped_to_its_own_resource(test_db):
    """``documents:read_all`` must not also unlock ``prompts``."""
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst, "scoped@resource-visibility-test.example")
    role = _make_role(test_db, "docs-only-admin", ["documents:read_all"])
    user.roles.append(role)
    test_db.commit()
    test_db.refresh(user)

    assert has_read_all_bypass(user, "documents") is True
    assert has_read_all_bypass(user, "prompts") is False


def test_unknown_resource_key_raises():
    with pytest.raises(KeyError):
        has_read_all_bypass(object(), "not-a-real-resource")
