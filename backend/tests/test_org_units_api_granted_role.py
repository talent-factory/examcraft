"""API tests for Granted Role on ``/api/v1/org-units/*`` (TF-637).

Pattern mirrors test_org_units_api.py. Covers: role_id on create/list/patch,
clearing role_id, the audit-log entries that must accompany
set/clear/assign/remove (org_units.py had zero audit coverage before
TF-637 -- this is new ground, not a pre-existing gap being extended), and
the PR-review fix that gates *granting* a role_id on the caller actually
holding the "admin" role or being a superuser -- without it, any holder of
the routinely-grantable ``manage_org_units`` permission could grant
themselves the global ``admin`` role via an OrgUnit and self-assign
membership, bypassing the stricter write-access gate that protects direct
role assignment (``api/admin.py::assign_role_to_user``).

Design: docs/superpowers/specs/2026-08-13-org-unit-rbac-vererbung-design.md
"""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import AuditLog, Institution, Role, User, UserStatus
from utils.auth_utils import get_current_user, get_current_active_user


@pytest.fixture(autouse=True)
def _clear_overrides_after_each_test():
    yield
    app.dependency_overrides.clear()


def _make_institution(db: Session, slug: str = "orgunit-granted-role") -> Institution:
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


def _make_admin(db: Session, institution_id: int, email: str) -> User:
    """A caller with ``manage_org_units`` only.

    Can manage OrgUnits (create/rename/move/delete, assign/remove
    members) and *clear* an existing role_id, but -- per the TF-637 review
    fix -- may NOT *grant* a role_id (that needs the "admin" role or
    superuser; see ``_make_institution_admin``).
    """
    role = Role(
        name=f"role_{email}",
        display_name="Test Admin",
        permissions=["manage_org_units"],
        is_system_role=False,
    )
    db.add(role)
    db.flush()
    user = User(
        email=email,
        first_name="Test",
        last_name="Admin",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()
    return user


def _make_institution_admin(db: Session, institution_id: int, email: str) -> User:
    """A caller holding the global "admin" role (by name) + manage_org_units.

    The only kind of caller allowed to *grant* a role_id after the TF-637
    review fix. The "admin" Role row is reused if another test module
    already seeded one into the shared test DB (established pattern, see
    test_admin_roles_api.py / test_audit_api.py -- Role.name is globally
    unique); its own permissions are irrelevant here since the gate only
    checks the role *name*, so manage_org_units is granted via a second,
    freshly-named role instead of depending on what permissions a reused
    "admin" row happens to carry.
    """
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role is None:
        admin_role = Role(
            name="admin",
            display_name="Administrator",
            permissions=["manage_users"],
            is_system_role=True,
        )
        db.add(admin_role)
        db.flush()
    manage_role = Role(
        # Role.name is varchar(50) and globally unique -- a short random
        # suffix (not the full email, unlike _make_admin's f"role_{email}")
        # keeps this under the limit regardless of email length.
        name=f"mou_{uuid.uuid4().hex[:12]}",
        display_name="Manage Org Units",
        permissions=["manage_org_units"],
        is_system_role=False,
    )
    db.add(manage_role)
    db.flush()
    user = User(
        email=email,
        first_name="Test",
        last_name="InstitutionAdmin",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    user.roles.append(admin_role)
    user.roles.append(manage_role)
    db.add(user)
    db.flush()
    return user


def _make_granted_role(db: Session, name: str, display_name: str) -> Role:
    role = Role(name=name, display_name=display_name, permissions=["submissions:grade"])
    db.add(role)
    db.flush()
    return role


def _client(test_db: Session, user: User) -> TestClient:
    import api.org_units as org_units_module

    if org_units_module.router not in app.router.routes:
        app.include_router(org_units_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def _audit_data(log_entry: AuditLog) -> dict:
    raw = log_entry.additional_data
    return json.loads(raw) if isinstance(raw, str) else (raw or {})


def test_create_org_unit_with_role_id_returns_role_name(test_db: Session) -> None:
    inst = _make_institution(test_db, "granted-create")
    admin = _make_institution_admin(test_db, inst.id, "admin@granted-create.ch")
    granted = _make_granted_role(test_db, "backend-grader-c1", "Backend-Grader")
    test_db.commit()

    client = _client(test_db, admin)
    response = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team Backend",
            "parent_org_unit_id": None,
            "role_id": granted.id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role_id"] == granted.id
    assert body["role_name"] == "Backend-Grader"

    log_entry = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == "set_org_unit_role",
            AuditLog.resource_id == str(body["id"]),
        )
        .one_or_none()
    )
    assert log_entry is not None
    assert log_entry.user_id == admin.id
    assert log_entry.resource_type == "org_unit"
    assert _audit_data(log_entry) == {"role_id": granted.id}


def test_create_org_unit_without_role_id_returns_null(test_db: Session) -> None:
    inst = _make_institution(test_db, "granted-create-null")
    admin = _make_admin(test_db, inst.id, "admin@granted-create-null.ch")
    test_db.commit()

    client = _client(test_db, admin)
    response = client.post(
        "/api/v1/org-units",
        json={"unit_type": "team", "name": "Team X", "parent_org_unit_id": None},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role_id"] is None
    assert body["role_name"] is None


def test_create_org_unit_with_role_id_without_admin_role_returns_403(
    test_db: Session,
) -> None:
    """TF-637 review fix: a caller with only ``manage_org_units`` (not the
    "admin" role, not superuser) must not be able to grant a role_id --
    otherwise they could grant themselves the global ``admin`` Role via an
    OrgUnit and self-assign membership into it."""
    inst = _make_institution(test_db, "granted-create-403")
    non_admin = _make_admin(test_db, inst.id, "non-admin@granted-create-403.ch")
    granted = _make_granted_role(test_db, "admin-lookalike-c", "Administrator")
    test_db.commit()

    client = _client(test_db, non_admin)
    response = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team X",
            "parent_org_unit_id": None,
            "role_id": granted.id,
        },
    )
    assert response.status_code == 403, response.text
    # and no OrgUnit should have been created as a side effect
    assert (
        test_db.query(AuditLog).filter(AuditLog.action == "set_org_unit_role").count()
        == 0
    )


def test_patch_sets_role_id_and_writes_audit_log(test_db: Session) -> None:
    inst = _make_institution(test_db, "granted-patch-set")
    admin = _make_institution_admin(test_db, inst.id, "admin@granted-patch-set.ch")
    granted = _make_granted_role(test_db, "backend-grader-c2", "Backend-Grader")
    client = _client(test_db, admin)
    create_response = client.post(
        "/api/v1/org-units",
        json={"unit_type": "team", "name": "Team Backend", "parent_org_unit_id": None},
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()

    response = client.patch(
        f"/api/v1/org-units/{org_unit_id}", json={"role_id": granted.id}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role_id"] == granted.id
    assert body["role_name"] == "Backend-Grader"

    log_entry = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == "set_org_unit_role",
            AuditLog.resource_id == str(org_unit_id),
        )
        .one_or_none()
    )
    assert log_entry is not None
    assert log_entry.user_id == admin.id
    assert log_entry.resource_type == "org_unit"
    assert _audit_data(log_entry) == {"old_role_id": None, "new_role_id": granted.id}


def test_patch_role_id_without_admin_role_returns_403(test_db: Session) -> None:
    """Same TF-637 review fix as the create-path 403 test, exercised via
    PATCH: manage_org_units alone must not be able to grant a role_id."""
    inst = _make_institution(test_db, "granted-patch-403")
    non_admin = _make_admin(test_db, inst.id, "non-admin@granted-patch-403.ch")
    granted = _make_granted_role(test_db, "admin-lookalike-p", "Administrator")
    client = _client(test_db, non_admin)
    create_response = client.post(
        "/api/v1/org-units",
        json={"unit_type": "team", "name": "Team X", "parent_org_unit_id": None},
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()

    response = client.patch(
        f"/api/v1/org-units/{org_unit_id}", json={"role_id": granted.id}
    )
    assert response.status_code == 403, response.text
    test_db.refresh(test_db.query(User).filter(User.id == non_admin.id).one())
    assert (
        test_db.query(AuditLog).filter(AuditLog.action == "set_org_unit_role").count()
        == 0
    )


def test_patch_role_id_same_value_writes_no_audit_log(test_db: Session) -> None:
    """PATCH-ing role_id to the value it already has must be a no-op --
    org_units.py explicitly guards on ``body.role_id != old_role_id``
    before flipping ``role_id_changed`` (and therefore before auditing)."""
    inst = _make_institution(test_db, "granted-patch-noop")
    admin = _make_institution_admin(test_db, inst.id, "admin@granted-patch-noop.ch")
    granted = _make_granted_role(test_db, "backend-grader-noop", "Backend-Grader")
    client = _client(test_db, admin)
    create_response = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team Backend",
            "parent_org_unit_id": None,
            "role_id": granted.id,
        },
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()
    audit_count_after_create = (
        test_db.query(AuditLog).filter(AuditLog.action == "set_org_unit_role").count()
    )
    assert audit_count_after_create == 1

    response = client.patch(
        f"/api/v1/org-units/{org_unit_id}", json={"role_id": granted.id}
    )
    assert response.status_code == 200, response.text
    assert response.json()["role_id"] == granted.id

    assert (
        test_db.query(AuditLog).filter(AuditLog.action == "set_org_unit_role").count()
        == audit_count_after_create
    ), "PATCH with the org-unit's existing role_id must not write another audit row"


def test_patch_clears_role_id_and_writes_audit_log(test_db: Session) -> None:
    inst = _make_institution(test_db, "granted-patch-clear")
    admin = _make_institution_admin(test_db, inst.id, "admin@granted-patch-clear.ch")
    granted = _make_granted_role(test_db, "backend-grader-c3", "Backend-Grader")
    client = _client(test_db, admin)
    create_response = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team Backend",
            "parent_org_unit_id": None,
            "role_id": granted.id,
        },
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()

    response = client.patch(f"/api/v1/org-units/{org_unit_id}", json={"role_id": None})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role_id"] is None
    assert body["role_name"] is None

    log_entry = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == "clear_org_unit_role",
            AuditLog.resource_id == str(org_unit_id),
        )
        .one_or_none()
    )
    assert log_entry is not None
    assert log_entry.resource_type == "org_unit"
    assert _audit_data(log_entry) == {"old_role_id": granted.id, "new_role_id": None}


def test_patch_clear_role_id_does_not_require_admin_role(test_db: Session) -> None:
    """Clearing a role_id can't escalate anything, so -- unlike granting
    one -- it must stay reachable with plain ``manage_org_units`` (no
    "admin" role needed). The org-unit itself is set up by an elevated
    admin (creation with a role_id needs the grant gate); the actual PATCH
    under test is performed by a plain manage_org_units caller."""
    inst = _make_institution(test_db, "granted-patch-clear-plain")
    elevated = _make_institution_admin(
        test_db, inst.id, "elevated@granted-patch-clear-plain.ch"
    )
    granted = _make_granted_role(
        test_db, "backend-grader-clear-plain", "Backend-Grader"
    )
    setup_client = _client(test_db, elevated)
    create_response = setup_client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team Backend",
            "parent_org_unit_id": None,
            "role_id": granted.id,
        },
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()

    plain_admin = _make_admin(test_db, inst.id, "plain@granted-patch-clear-plain.ch")
    test_db.commit()
    client = _client(test_db, plain_admin)
    response = client.patch(f"/api/v1/org-units/{org_unit_id}", json={"role_id": None})
    assert response.status_code == 200, response.text
    assert response.json()["role_id"] is None


def test_patch_without_role_id_field_leaves_existing_role_unchanged(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db, "granted-patch-untouched")
    admin = _make_institution_admin(
        test_db, inst.id, "admin@granted-patch-untouched.ch"
    )
    granted = _make_granted_role(test_db, "backend-grader-c4", "Backend-Grader")
    client = _client(test_db, admin)
    create_response = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team Backend",
            "parent_org_unit_id": None,
            "role_id": granted.id,
        },
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()

    response = client.patch(
        f"/api/v1/org-units/{org_unit_id}", json={"name": "Team Backend Renamed"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Team Backend Renamed"
    assert body["role_id"] == granted.id
    assert body["role_name"] == "Backend-Grader"


def test_create_org_unit_with_unknown_role_id_returns_404(test_db: Session) -> None:
    inst = _make_institution(test_db, "granted-unknown-role")
    admin = _make_institution_admin(test_db, inst.id, "admin@granted-unknown-role.ch")
    test_db.commit()

    client = _client(test_db, admin)
    response = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team X",
            "parent_org_unit_id": None,
            "role_id": 999999,
        },
    )
    assert response.status_code == 404


def test_patch_org_unit_with_unknown_role_id_returns_404(test_db: Session) -> None:
    """PATCH counterpart of the create-path 404 test above -- previously
    untested, so a regression that broke 404-on-PATCH only (e.g. dropping
    the ``_load_role_for_institution`` call on just the update path) would
    not have been caught."""
    inst = _make_institution(test_db, "granted-patch-unknown-role")
    admin = _make_institution_admin(
        test_db, inst.id, "admin@granted-patch-unknown-role.ch"
    )
    client = _client(test_db, admin)
    create_response = client.post(
        "/api/v1/org-units",
        json={"unit_type": "team", "name": "Team X", "parent_org_unit_id": None},
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()

    response = client.patch(
        f"/api/v1/org-units/{org_unit_id}", json={"role_id": 999999}
    )
    assert response.status_code == 404


def test_list_org_units_includes_role_name(test_db: Session) -> None:
    inst = _make_institution(test_db, "granted-list")
    admin = _make_institution_admin(test_db, inst.id, "admin@granted-list.ch")
    granted = _make_granted_role(test_db, "backend-grader-c5", "Backend-Grader")
    client = _client(test_db, admin)
    client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team Backend",
            "parent_org_unit_id": None,
            "role_id": granted.id,
        },
    )
    test_db.commit()

    response = client.get("/api/v1/org-units")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["role_name"] == "Backend-Grader"


def test_assign_member_writes_audit_log(test_db: Session) -> None:
    """TF-637 review fix: membership assignment is the step that actually
    confers a Granted Role's permissions to a specific person, so it must
    be audited just like set/clear of role_id itself."""
    inst = _make_institution(test_db, "granted-assign-audit")
    admin = _make_institution_admin(test_db, inst.id, "admin@granted-assign-audit.ch")
    granted = _make_granted_role(test_db, "backend-grader-assign", "Backend-Grader")
    member = User(
        email="member@granted-assign-audit.ch",
        first_name="Member",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(member)
    test_db.flush()
    client = _client(test_db, admin)
    create_response = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team Backend",
            "parent_org_unit_id": None,
            "role_id": granted.id,
        },
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()

    response = client.post(
        f"/api/v1/org-units/{org_unit_id}/members", json={"user_id": member.id}
    )
    assert response.status_code == 201, response.text

    log_entry = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == "assign_org_unit_member",
            AuditLog.resource_id == str(org_unit_id),
        )
        .one_or_none()
    )
    assert log_entry is not None
    assert log_entry.user_id == admin.id
    assert log_entry.resource_type == "org_unit"
    assert _audit_data(log_entry) == {
        "org_unit_id": org_unit_id,
        "user_id": member.id,
    }


def test_remove_member_writes_audit_log(test_db: Session) -> None:
    inst = _make_institution(test_db, "granted-remove-audit")
    admin = _make_institution_admin(test_db, inst.id, "admin@granted-remove-audit.ch")
    member = User(
        email="member@granted-remove-audit.ch",
        first_name="Member",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(member)
    test_db.flush()
    client = _client(test_db, admin)
    create_response = client.post(
        "/api/v1/org-units",
        json={"unit_type": "team", "name": "Team Backend", "parent_org_unit_id": None},
    )
    org_unit_id = create_response.json()["id"]
    test_db.commit()
    client.post(f"/api/v1/org-units/{org_unit_id}/members", json={"user_id": member.id})
    test_db.commit()

    response = client.delete(f"/api/v1/org-units/{org_unit_id}/members/{member.id}")
    assert response.status_code == 204, response.text

    log_entry = (
        test_db.query(AuditLog)
        .filter(
            AuditLog.action == "remove_org_unit_member",
            AuditLog.resource_id == str(org_unit_id),
        )
        .one_or_none()
    )
    assert log_entry is not None
    assert log_entry.resource_type == "org_unit"
    assert _audit_data(log_entry) == {
        "org_unit_id": org_unit_id,
        "user_id": member.id,
    }


def test_me_endpoint_surfaces_granted_role_permission(test_db: Session) -> None:
    """TF-637 review fix: a Granted Role's permissions must reach the
    frontend's ``roles[]`` payload (``AuthContext.tsx``/
    ``PermissionGuard.tsx`` read permissions exclusively from there), not
    just satisfy backend ``has_permission()`` checks -- otherwise a user
    who inherits a permission via Org-Unit membership passes every backend
    check but sees no UI for it."""
    import api.auth as auth_module
    from services.org_unit_service import assign_user_to_org_unit

    inst = _make_institution(test_db, "granted-me-endpoint")
    granted = _make_granted_role(test_db, "backend-grader-me", "Backend-Grader")
    member = User(
        email="member@granted-me-endpoint.ch",
        first_name="Member",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(member)
    test_db.flush()
    from models.org_unit import OrgUnit

    org_unit = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        role_id=granted.id,
    )
    test_db.add(org_unit)
    test_db.flush()
    assign_user_to_org_unit(test_db, user_id=member.id, org_unit_id=org_unit.id)
    test_db.commit()
    test_db.refresh(member)

    if auth_module.router not in app.router.routes:
        app.include_router(auth_module.router)
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: member
    app.dependency_overrides[get_current_active_user] = lambda: member
    client = TestClient(app, raise_server_exceptions=True)

    response = client.get("/api/auth/me")
    assert response.status_code == 200, response.text
    body = response.json()
    all_permissions = {perm for role in body["roles"] for perm in role["permissions"]}
    assert "submissions:grade" in all_permissions
    assert any(role["id"] == granted.id for role in body["roles"])
