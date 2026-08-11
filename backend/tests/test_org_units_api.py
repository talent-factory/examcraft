"""API tests for ``/api/v1/org-units/*`` (Stufe 0 Fundament).

Pattern mirrors test_grading_schemes_api.py: a helper builds an isolated
institution + user per test, the TestClient overrides get_db/get_current_user,
and the test inspects HTTP responses end-to-end against the real DB.

Design: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, Role, User, UserStatus
from models.org_unit import OrgUnit
from utils.auth_utils import get_current_user, get_current_active_user


@pytest.fixture(autouse=True)
def _clear_overrides_after_each_test():
    yield
    app.dependency_overrides.clear()


def _make_institution(db: Session, slug: str = "orgunit-api") -> Institution:
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


def _make_user_with_perms(
    db: Session,
    institution_id: int,
    *,
    permissions: list[str],
    email: str = "admin@orgunit-api.ch",
) -> User:
    role = Role(
        name=f"role_{email}",
        display_name="Test Role",
        permissions=permissions,
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


def _client(test_db: Session, user: User) -> TestClient:
    import api.org_units as org_units_module

    if org_units_module.router not in app.router.routes:
        app.include_router(org_units_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def test_create_and_list_org_unit(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(test_db, inst.id, permissions=["manage_org_units"])
    test_db.commit()

    client = _client(test_db, user)
    create_response = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "abteilung",
            "name": "Informatik",
            "parent_org_unit_id": None,
        },
    )
    assert create_response.status_code == 201, create_response.text
    body = create_response.json()
    assert body["name"] == "Informatik"
    assert body["parent_org_unit_id"] is None
    assert body["descendant_count"] == 0

    list_response = client.get("/api/v1/org-units")
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Informatik"


def test_create_without_permission_returns_403(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-403")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["submissions:read"],
        email="reader@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "X", "parent_org_unit_id": None},
    )
    assert response.status_code == 403


def test_create_duplicate_sibling_name_returns_409(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-409")
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["manage_org_units"], email="dup@orgunit-api.ch"
    )
    test_db.commit()

    client = _client(test_db, user)
    client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "IT", "parent_org_unit_id": None},
    )
    response = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "IT", "parent_org_unit_id": None},
    )
    assert response.status_code == 409


def test_rename_to_existing_sibling_name_returns_409(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-rename-409")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="renamer@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    abteilung_a = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    abteilung_b = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "B", "parent_org_unit_id": None},
    ).json()

    response = client.patch(
        f"/api/v1/org-units/{abteilung_b['id']}",
        json={"name": abteilung_a["name"]},
    )
    assert response.status_code == 409


def test_move_org_unit_updates_parent(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-move")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="mover@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    abteilung_a = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    abteilung_b = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "B", "parent_org_unit_id": None},
    ).json()
    team = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "Team",
            "parent_org_unit_id": abteilung_a["id"],
        },
    ).json()

    response = client.patch(
        f"/api/v1/org-units/{team['id']}",
        json={"parent_org_unit_id": abteilung_b["id"]},
    )
    assert response.status_code == 200
    assert response.json()["parent_org_unit_id"] == abteilung_b["id"]


def test_patch_null_parent_without_move_to_root_returns_422(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-null-parent-422")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="ambiguous@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    team = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "T",
            "parent_org_unit_id": abteilung["id"],
        },
    ).json()

    response = client.patch(
        f"/api/v1/org-units/{team['id']}",
        json={"parent_org_unit_id": None},
    )
    assert response.status_code == 422


def test_patch_move_to_root_with_null_parent_returns_200(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-move-to-root")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="root-mover@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    team = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "T",
            "parent_org_unit_id": abteilung["id"],
        },
    ).json()

    response = client.patch(
        f"/api/v1/org-units/{team['id']}",
        json={"parent_org_unit_id": None, "move_to_root": True},
    )
    assert response.status_code == 200
    assert response.json()["parent_org_unit_id"] is None


def test_move_org_unit_rejecting_cycle_returns_409(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-move-cycle")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="cycle@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    team = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "T",
            "parent_org_unit_id": abteilung["id"],
        },
    ).json()

    response = client.patch(
        f"/api/v1/org-units/{abteilung['id']}",
        json={"parent_org_unit_id": team["id"]},
    )
    assert response.status_code == 409


def test_delete_org_unit_cascades_and_returns_204(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-delete")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="deleter@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    team = client.post(
        "/api/v1/org-units",
        json={
            "unit_type": "team",
            "name": "T",
            "parent_org_unit_id": abteilung["id"],
        },
    ).json()

    response = client.delete(f"/api/v1/org-units/{abteilung['id']}")
    assert response.status_code == 204
    assert test_db.query(OrgUnit).filter(OrgUnit.id == team["id"]).one_or_none() is None


def test_list_org_units_is_scoped_per_institution(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="orgunit-api-list-scope-a")
    inst_b = _make_institution(test_db, slug="orgunit-api-list-scope-b")
    user_a = _make_user_with_perms(
        test_db,
        inst_a.id,
        permissions=["manage_org_units"],
        email="list-a@orgunit-api.ch",
    )
    user_b = _make_user_with_perms(
        test_db,
        inst_b.id,
        permissions=["manage_org_units"],
        email="list-b@orgunit-api.ch",
    )
    test_db.commit()

    client_a = _client(test_db, user_a)
    client_a.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A-only", "parent_org_unit_id": None},
    )

    client_b = _client(test_db, user_b)
    response = client_b.get("/api/v1/org-units")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_get_org_unit_from_other_institution_returns_404_not_403(
    test_db: Session,
) -> None:
    """Cross-tenant access is 404, not 403 -- matches _load_org_unit_for_user's
    intentional existence-hiding pattern (see student_classes.py)."""
    inst_a = _make_institution(test_db, slug="orgunit-api-cross-a")
    inst_b = _make_institution(test_db, slug="orgunit-api-cross-b")
    user_a = _make_user_with_perms(
        test_db,
        inst_a.id,
        permissions=["manage_org_units"],
        email="cross-a@orgunit-api.ch",
    )
    user_b = _make_user_with_perms(
        test_db,
        inst_b.id,
        permissions=["manage_org_units"],
        email="cross-b@orgunit-api.ch",
    )
    test_db.commit()

    foreign_unit = (
        _client(test_db, user_a)
        .post(
            "/api/v1/org-units",
            json={
                "unit_type": "abteilung",
                "name": "Foreign",
                "parent_org_unit_id": None,
            },
        )
        .json()
    )

    client_b = _client(test_db, user_b)

    patch_response = client_b.patch(
        f"/api/v1/org-units/{foreign_unit['id']}", json={"name": "Hijacked"}
    )
    assert patch_response.status_code == 404

    delete_response = client_b.delete(f"/api/v1/org-units/{foreign_unit['id']}")
    assert delete_response.status_code == 404

    member_response = client_b.post(
        f"/api/v1/org-units/{foreign_unit['id']}/members",
        json={"user_id": user_b.id, "role": None},
    )
    assert member_response.status_code == 404


def test_update_delete_move_assign_remove_without_permission_return_403(
    test_db: Session,
) -> None:
    """RBAC 403 is only ever exercised for POST elsewhere -- the other four
    endpoints each carry their own independent require_permission dependency
    and deserve the same regression coverage."""
    inst = _make_institution(test_db, slug="orgunit-api-403-breadth")
    admin = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="breadth-admin@orgunit-api.ch",
    )
    test_db.commit()

    admin_client = _client(test_db, admin)
    abteilung = admin_client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    other_abteilung = admin_client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "B", "parent_org_unit_id": None},
    ).json()
    member = User(
        email="breadth-member@orgunit-api.ch",
        first_name="Member",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(member)
    test_db.commit()
    admin_client.post(
        f"/api/v1/org-units/{abteilung['id']}/members",
        json={"user_id": member.id, "role": None},
    )

    reader = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["submissions:read"],
        email="breadth-reader@orgunit-api.ch",
    )
    test_db.commit()
    reader_client = _client(test_db, reader)

    assert (
        reader_client.patch(
            f"/api/v1/org-units/{abteilung['id']}", json={"name": "Renamed"}
        ).status_code
        == 403
    )
    assert (
        reader_client.patch(
            f"/api/v1/org-units/{abteilung['id']}",
            json={"parent_org_unit_id": other_abteilung["id"]},
        ).status_code
        == 403
    )
    assert (
        reader_client.post(
            f"/api/v1/org-units/{other_abteilung['id']}/members",
            json={"user_id": member.id, "role": None},
        ).status_code
        == 403
    )
    assert (
        reader_client.delete(
            f"/api/v1/org-units/{abteilung['id']}/members/{member.id}"
        ).status_code
        == 403
    )
    assert (
        reader_client.delete(f"/api/v1/org-units/{abteilung['id']}").status_code == 403
    )


def test_patch_move_to_root_with_non_null_parent_returns_422(test_db: Session) -> None:
    """Mirror-image of test_patch_null_parent_without_move_to_root_returns_422:
    move_to_root=true + an explicit non-null parent_org_unit_id is the other
    half of the same ambiguity and must be rejected the same way, not silently
    resolved by dropping the parent value."""
    inst = _make_institution(test_db, slug="orgunit-api-move-root-ambiguous")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="move-root-ambiguous@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    abteilung_a = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    abteilung_b = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "B", "parent_org_unit_id": None},
    ).json()

    response = client.patch(
        f"/api/v1/org-units/{abteilung_b['id']}",
        json={"parent_org_unit_id": abteilung_a["id"], "move_to_root": True},
    )
    assert response.status_code == 422
    # The parent must remain unchanged -- the earlier (fixed) behaviour was to
    # silently drop it and detach to root instead of rejecting.
    assert (
        test_db.query(OrgUnit)
        .filter(OrgUnit.id == abteilung_b["id"])
        .one()
        .parent_org_unit_id
        is None
    )


def test_create_org_unit_rejects_unknown_unit_type(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-unknown-type")
    user = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="unknown-type@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilnug", "name": "Typo", "parent_org_unit_id": None},
    )
    assert response.status_code == 422


def test_assign_member_from_other_institution_returns_404(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="orgunit-api-member-cross-a")
    inst_b = _make_institution(test_db, slug="orgunit-api-member-cross-b")
    admin_a = _make_user_with_perms(
        test_db,
        inst_a.id,
        permissions=["manage_org_units"],
        email="member-cross-admin@orgunit-api.ch",
    )
    foreign_user = User(
        email="member-cross-foreign@orgunit-api.ch",
        first_name="Foreign",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst_b.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(foreign_user)
    test_db.commit()

    client = _client(test_db, admin_a)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()

    response = client.post(
        f"/api/v1/org-units/{abteilung['id']}/members",
        json={"user_id": foreign_user.id, "role": None},
    )
    assert response.status_code == 404


def test_assign_duplicate_member_returns_409(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-member-dup")
    admin = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="member-dup-admin@orgunit-api.ch",
    )
    member = User(
        email="member-dup-target@orgunit-api.ch",
        first_name="Member",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(member)
    test_db.commit()

    client = _client(test_db, admin)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    client.post(
        f"/api/v1/org-units/{abteilung['id']}/members",
        json={"user_id": member.id, "role": None},
    )

    response = client.post(
        f"/api/v1/org-units/{abteilung['id']}/members",
        json={"user_id": member.id, "role": None},
    )
    assert response.status_code == 409


def test_remove_unknown_member_returns_404(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-member-remove-404")
    admin = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="member-remove-admin@orgunit-api.ch",
    )
    never_assigned = User(
        email="member-remove-target@orgunit-api.ch",
        first_name="Never",
        last_name="Assigned",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(never_assigned)
    test_db.commit()

    client = _client(test_db, admin)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()

    response = client.delete(
        f"/api/v1/org-units/{abteilung['id']}/members/{never_assigned.id}"
    )
    assert response.status_code == 404


def test_delete_org_unit_with_active_member_cascades_membership(
    test_db: Session,
) -> None:
    """Deleting an OrgUnit that still has active UserOrgUnit memberships must
    not error -- the FK's ON DELETE CASCADE (see the migration) removes the
    membership row along with the OrgUnit."""
    inst = _make_institution(test_db, slug="orgunit-api-delete-with-member")
    admin = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="delete-with-member-admin@orgunit-api.ch",
    )
    member = User(
        email="delete-with-member-target@orgunit-api.ch",
        first_name="Member",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(member)
    test_db.commit()

    client = _client(test_db, admin)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()
    assign_response = client.post(
        f"/api/v1/org-units/{abteilung['id']}/members",
        json={"user_id": member.id, "role": None},
    )
    assert assign_response.status_code == 201

    delete_response = client.delete(f"/api/v1/org-units/{abteilung['id']}")
    assert delete_response.status_code == 204

    from models.org_unit import UserOrgUnit

    remaining = (
        test_db.query(UserOrgUnit)
        .filter(
            UserOrgUnit.user_id == member.id, UserOrgUnit.org_unit_id == abteilung["id"]
        )
        .one_or_none()
    )
    assert remaining is None


def test_delete_org_unit_referenced_by_document_returns_409(test_db: Session) -> None:
    """API-layer counterpart to
    test_tf620_team_org_unit_visibility.test_delete_org_unit_referenced_by_document_raises
    -- that test only exercises the service function's ValueError; this one
    verifies the ValueError -> HTTPException(409) mapping in
    delete_org_unit_endpoint itself (TF-620)."""
    from models.document import Document, DocumentStatus, DocumentVisibility

    inst = _make_institution(test_db, slug="orgunit-api-409-doc")
    admin = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="delete-doc-ref-admin@orgunit-api.ch",
    )
    test_db.commit()

    client = _client(test_db, admin)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()

    doc = Document(
        filename="ref.pdf",
        original_filename="ref.pdf",
        file_path="/tmp/ref.pdf",
        file_size=1,
        mime_type="application/pdf",
        status=DocumentStatus.PROCESSED,
        institution_id=inst.id,
        user_id=admin.id,
        visibility=DocumentVisibility.TEAM,
        org_unit_id=abteilung["id"],
    )
    test_db.add(doc)
    test_db.commit()

    delete_response = client.delete(f"/api/v1/org-units/{abteilung['id']}")
    assert delete_response.status_code == 409
    assert "Dokumente" in delete_response.json()["detail"]

    # The org unit must still exist -- the failed delete didn't half-apply.
    assert (
        test_db.query(OrgUnit).filter_by(id=abteilung["id"]).one_or_none() is not None
    )


def test_assign_and_remove_member(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="orgunit-api-members")
    admin = _make_user_with_perms(
        test_db,
        inst.id,
        permissions=["manage_org_units"],
        email="admin2@orgunit-api.ch",
    )
    member = User(
        email="member@orgunit-api.ch",
        first_name="Member",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(member)
    test_db.commit()

    client = _client(test_db, admin)
    abteilung = client.post(
        "/api/v1/org-units",
        json={"unit_type": "abteilung", "name": "A", "parent_org_unit_id": None},
    ).json()

    assign_response = client.post(
        f"/api/v1/org-units/{abteilung['id']}/members",
        json={"user_id": member.id, "role": None},
    )
    assert assign_response.status_code == 201

    remove_response = client.delete(
        f"/api/v1/org-units/{abteilung['id']}/members/{member.id}"
    )
    assert remove_response.status_code == 204
