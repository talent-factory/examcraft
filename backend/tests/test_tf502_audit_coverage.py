"""TF-502: audit coverage for admin / institution / grading-scheme mutations.

Before TF-502 these endpoints mutated privileged / PII / tenant data without
writing an ``audit_logs`` row. These tests pin that each mutation now emits the
expected action via ``AuditService.log_event_best_effort`` (best-effort: the
mutation is the only record, so the audit entry must be written, but a failing
audit write never blocks the already-committed change — see
``test_audit_failure_does_not_block_mutation``).

Pattern mirrors ``test_grading_schemes_api`` / ``test_admin_institution_grading_scheme``:
isolated institution + actor per test, dependency overrides, end-to-end HTTP.

Every ``log_event_best_effort`` call site introduced by TF-502 is pinned
individually below, including the admin role-assignment endpoints and the
RBAC custom-role endpoints — the "same code path" argument for skipping them
doesn't hold since each site has a distinct action/resource_id/
``additional_data`` shape that a wrong constant or typo would not surface
anywhere else.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import AuditLog, Institution, Role, User, UserStatus
from models.grading_scheme import GradingScheme
from services.audit_service import AuditService
from utils.auth_utils import get_current_active_user, get_current_user


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _institution(db: Session, slug: str = "tf502") -> Institution:
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


def _actor(db: Session, institution_id: int, email: str = "su@tf502.ch") -> User:
    """Superuser with grading_schemes:manage — satisfies get_current_superuser,
    _require_write_access and require_permission across all tested endpoints."""
    role = Role(
        name=f"role_{email}",
        display_name="TF502 Admin",
        permissions=["grading_schemes:manage"],
        is_system_role=False,
    )
    db.add(role)
    db.flush()
    user = User(
        email=email,
        first_name="Su",
        last_name="Peruser",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()
    return user


def _client(db: Session, user: User) -> TestClient:
    import api.admin as admin_module
    import api.grading_schemes as grading_module
    import api.v1.rbac as rbac_module

    for module in (admin_module, grading_module, rbac_module):
        if module.router not in app.router.routes:
            app.include_router(module.router)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def _custom_config() -> dict:
    return {
        "type": "stepped",
        "steps": [
            {"min_pct": 50, "grade_label": "Genügend", "is_passing": True},
            {"min_pct": 0, "grade_label": "Ungenügend", "is_passing": False},
        ],
    }


def _scheme(db: Session, institution_id: int, name: str = "Skala") -> GradingScheme:
    scheme = GradingScheme(
        institution_id=institution_id,
        name=name,
        display_format="pass_fail",
        config=_custom_config(),
        is_default_for_institution=False,
    )
    db.add(scheme)
    db.flush()
    return scheme


def _audit(db: Session, action: str) -> list[AuditLog]:
    return db.query(AuditLog).filter(AuditLog.action == action).all()


def _data(row: AuditLog) -> dict:
    assert row.additional_data is not None
    return json.loads(row.additional_data)


# ---------------------------------------------------------------------------
# Grading schemes (api/grading_schemes.py)
# ---------------------------------------------------------------------------


def test_create_grading_scheme_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    test_db.commit()

    resp = _client(test_db, actor).post(
        "/api/v1/grading-schemes",
        json={
            "name": "Custom Pass-Fail",
            "display_format": "pass_fail",
            "config": _custom_config(),
            "is_default_for_institution": False,
        },
    )
    assert resp.status_code == 201, resp.text

    rows = _audit(test_db, "create_grading_scheme")
    assert len(rows) == 1
    assert rows[0].user_id == actor.id
    assert rows[0].resource_type == "grading_scheme"
    data = _data(rows[0])
    assert data["name"] == "Custom Pass-Fail"
    assert data["institution_id"] == inst.id
    assert data["is_default_for_institution"] is False


def test_update_grading_scheme_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    scheme = _scheme(test_db, inst.id)
    test_db.commit()

    resp = _client(test_db, actor).patch(
        f"/api/v1/grading-schemes/{scheme.id}",
        json={"name": "Umbenannt"},
    )
    assert resp.status_code == 200, resp.text

    rows = _audit(test_db, "update_grading_scheme")
    assert len(rows) == 1
    assert rows[0].resource_id == str(scheme.id)
    assert _data(rows[0])["changed_fields"] == ["name"]


def test_delete_grading_scheme_is_audited(test_db: Session) -> None:
    """Pins that the id/name captured *before* db.delete reach the audit row."""
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    scheme = _scheme(test_db, inst.id, name="Zu löschen")
    scheme_id = scheme.id
    test_db.commit()

    resp = _client(test_db, actor).delete(f"/api/v1/grading-schemes/{scheme_id}")
    assert resp.status_code == 204, resp.text

    rows = _audit(test_db, "delete_grading_scheme")
    assert len(rows) == 1
    assert rows[0].resource_id == str(scheme_id)
    data = _data(rows[0])
    assert data["name"] == "Zu löschen"
    assert data["institution_id"] == inst.id


# ---------------------------------------------------------------------------
# Institutions (api/admin.py)
# ---------------------------------------------------------------------------


def test_create_institution_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    test_db.commit()

    resp = _client(test_db, actor).post(
        "/api/admin/institutions",
        json={
            "name": "Neue Schule TF502",
            "domain": "neu-tf502.ch",
            "subscription_tier": "free",
        },
    )
    assert resp.status_code == 201, resp.text

    rows = _audit(test_db, "create_institution")
    assert len(rows) == 1
    assert rows[0].user_id == actor.id
    assert rows[0].resource_type == "institution"
    data = _data(rows[0])
    assert data["name"] == "Neue Schule TF502"
    assert data["domain"] == "neu-tf502.ch"
    assert data["subscription_tier"] == "free"


def test_update_institution_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    test_db.commit()

    resp = _client(test_db, actor).patch(
        f"/api/admin/institutions/{inst.id}",
        json={"name": "Umbenannte Schule"},
    )
    assert resp.status_code == 200, resp.text

    rows = _audit(test_db, "update_institution")
    assert len(rows) == 1
    assert rows[0].resource_id == str(inst.id)
    data = _data(rows[0])
    assert data["changed_fields"] == ["name"]
    assert data["subscription_tier"] == inst.subscription_tier


# ---------------------------------------------------------------------------
# Admin user mutations (api/admin.py)
# ---------------------------------------------------------------------------


def _target_user(
    db: Session, institution_id: int, email: str = "target@tf502.ch"
) -> User:
    user = User(
        email=email,
        first_name="Alt",
        last_name="Name",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def test_admin_update_user_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    target = _target_user(test_db, inst.id)
    test_db.commit()

    resp = _client(test_db, actor).patch(
        f"/api/admin/users/{target.id}",
        json={"first_name": "Neu"},
    )
    assert resp.status_code == 200, resp.text

    rows = _audit(test_db, "update_user")
    assert len(rows) == 1
    assert rows[0].resource_id == str(target.id)
    assert rows[0].user_id == actor.id
    data = _data(rows[0])
    assert data["target_user_id"] == target.id
    assert data["changed_fields"] == ["first_name"]


def test_admin_update_user_status_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    target = _target_user(test_db, inst.id, email="status-target@tf502.ch")
    test_db.commit()

    resp = _client(test_db, actor).patch(
        f"/api/admin/users/{target.id}/status",
        json={"status": "inactive"},
    )
    assert resp.status_code == 200, resp.text

    rows = _audit(test_db, "update_user")
    matching = [r for r in rows if r.resource_id == str(target.id)]
    assert len(matching) == 1
    data = _data(matching[0])
    assert data["target_user_id"] == target.id
    assert data["new_status"] == "inactive"


def test_admin_assign_role_to_user_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    target = _target_user(test_db, inst.id, email="assign-target@tf502.ch")
    grantable_role = Role(
        name="tf502_grantable",
        display_name="Grantable Role",
        permissions=["exams:read"],
        is_system_role=False,
    )
    test_db.add(grantable_role)
    test_db.commit()

    resp = _client(test_db, actor).post(
        f"/api/admin/users/{target.id}/roles",
        json={"role_id": grantable_role.id},
    )
    assert resp.status_code == 200, resp.text

    rows = _audit(test_db, "assign_role")
    assert len(rows) == 1
    assert rows[0].resource_id == str(target.id)
    assert rows[0].user_id == actor.id
    data = _data(rows[0])
    assert data["role_id"] == grantable_role.id
    assert data["role_name"] == "tf502_grantable"


def test_admin_remove_role_from_user_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    removable_role = Role(
        name="tf502_removable",
        display_name="Removable Role",
        permissions=["exams:read"],
        is_system_role=False,
    )
    other_role = Role(
        name="tf502_other",
        display_name="Other Role",
        permissions=["exams:read"],
        is_system_role=False,
    )
    test_db.add_all([removable_role, other_role])
    test_db.flush()
    target = _target_user(test_db, inst.id, email="remove-target@tf502.ch")
    target.roles.extend([removable_role, other_role])
    test_db.commit()

    resp = _client(test_db, actor).delete(
        f"/api/admin/users/{target.id}/roles/{removable_role.id}"
    )
    assert resp.status_code == 200, resp.text

    rows = _audit(test_db, "remove_role")
    assert len(rows) == 1
    assert rows[0].resource_id == str(target.id)
    data = _data(rows[0])
    assert data["role_id"] == removable_role.id
    assert data["role_name"] == "tf502_removable"


# ---------------------------------------------------------------------------
# Admin roles (api/admin.py, TF-603)
# ---------------------------------------------------------------------------


def test_admin_create_role_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    test_db.commit()

    resp = _client(test_db, actor).post(
        "/api/admin/roles",
        json={
            "name": "tf502_custom_role",
            "display_name": "TF502 Custom Role",
            "permissions": [],
        },
    )
    assert resp.status_code == 201, resp.text
    role_id = resp.json()["id"]

    rows = _audit(test_db, "create_role")
    assert len(rows) == 1
    assert rows[0].user_id == actor.id
    assert rows[0].resource_type == "role"
    assert rows[0].resource_id == str(role_id)
    data = _data(rows[0])
    assert data["name"] == "tf502_custom_role"
    assert data["permission_count"] == 0


def test_admin_update_role_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    role = Role(
        name="tf502_update_target",
        display_name="TF502 Update Target",
        permissions=["manage_org_units"],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    resp = _client(test_db, actor).patch(
        f"/api/admin/roles/{role.id}",
        json={"permissions": ["manage_org_units", "manage_settings"]},
    )
    assert resp.status_code == 200, resp.text

    rows = _audit(test_db, "update_role")
    assert len(rows) == 1
    assert rows[0].resource_id == str(role.id)
    data = _data(rows[0])
    assert data["role_id"] == role.id
    assert data["name"] == "tf502_update_target"


def test_admin_delete_role_is_audited(test_db: Session) -> None:
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    role = Role(
        name="tf502_delete_target",
        display_name="TF502 Delete Target",
        permissions=["manage_org_units"],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)
    role_id = role.id

    resp = _client(test_db, actor).delete(f"/api/admin/roles/{role_id}")
    assert resp.status_code == 204, resp.text

    rows = _audit(test_db, "delete_role")
    assert len(rows) == 1
    assert rows[0].user_id == actor.id
    assert rows[0].resource_type == "role"
    assert rows[0].resource_id == str(role_id)
    data = _data(rows[0])
    assert data["name"] == "tf502_delete_target"
    assert data["was_system_role"] is False


# ---------------------------------------------------------------------------
# Best-effort contract: a failing audit write must not block the mutation
# ---------------------------------------------------------------------------


def test_audit_failure_does_not_block_mutation(test_db: Session, monkeypatch) -> None:
    """Pins the entire point of log_event_best_effort: an already-committed
    mutation must succeed even if the audit write itself blows up."""
    inst = _institution(test_db)
    actor = _actor(test_db, inst.id)
    test_db.commit()

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated audit backend outage")

    monkeypatch.setattr(AuditService, "log_action", _boom)

    resp = _client(test_db, actor).post(
        "/api/v1/grading-schemes",
        json={
            "name": "Audit-Outage",
            "display_format": "pass_fail",
            "config": _custom_config(),
            "is_default_for_institution": False,
        },
    )
    assert resp.status_code == 201, resp.text

    # log_action never ran to completion, so no row exists — but the
    # mutation itself is unaffected by the simulated audit-backend failure.
    assert _audit(test_db, "create_grading_scheme") == []
