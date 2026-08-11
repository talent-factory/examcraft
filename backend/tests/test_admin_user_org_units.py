"""
Tests for org_units field on UserDetailResponse (TF-602).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import User, Institution, UserStatus
from models.org_unit import OrgUnit, UserOrgUnit
from utils.auth_utils import get_current_user


@pytest.fixture(autouse=True)
def _clear_overrides_after_each_test():
    yield
    app.dependency_overrides.clear()


def _make_institution(db: Session, slug: str = "admin-user-org-units") -> Institution:
    """Create test institution."""
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


def _make_superuser(db: Session, institution_id: int) -> User:
    """Create superuser."""
    user = User(
        email="admin@admin-org-units-field-test.ch",
        first_name="Super",
        last_name="User",
        password_hash="fake_hash",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    return user


def _make_member_user(db: Session, institution_id: int) -> User:
    """Create regular user for testing org_unit membership."""
    user = User(
        email="member@admin-org-units-field-test.ch",
        first_name="John",
        last_name="Doe",
        password_hash="fake_hash",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    db.add(user)
    db.flush()
    return user


def _client(test_db: Session, user: User) -> TestClient:
    """Create TestClient with given user authenticated."""
    import api.admin as admin_module

    if admin_module.router not in app.router.routes:
        app.include_router(admin_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def test_user_detail_includes_org_units_empty(test_db: Session) -> None:
    """Test that user detail response includes org_units field (empty when no memberships)."""
    inst = _make_institution(test_db)
    superuser = _make_superuser(test_db, inst.id)
    member_user = _make_member_user(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, superuser)
    response = client.get(f"/api/admin/users/{member_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert "org_units" in data
    assert data["org_units"] == []


def test_user_detail_includes_org_units_with_multiple_memberships(
    test_db: Session,
) -> None:
    """Test that org_units field lists ALL of a user's memberships (multi-membership case)."""
    inst = _make_institution(test_db, slug="admin-user-org-units-multi")
    superuser = _make_superuser(test_db, inst.id)
    member_user = _make_member_user(test_db, inst.id)
    test_db.flush()

    abteilung = OrgUnit(
        institution_id=inst.id,
        parent_org_unit_id=None,
        unit_type="abteilung",
        name="Informatik",
    )
    test_db.add(abteilung)
    test_db.flush()

    team_a = OrgUnit(
        institution_id=inst.id,
        parent_org_unit_id=abteilung.id,
        unit_type="team",
        name="Backend",
    )
    team_b = OrgUnit(
        institution_id=inst.id,
        parent_org_unit_id=abteilung.id,
        unit_type="team",
        name="Frontend",
    )
    test_db.add_all([team_a, team_b])
    test_db.flush()

    test_db.add(
        UserOrgUnit(user_id=member_user.id, org_unit_id=team_a.id, role="Leiter")
    )
    test_db.add(UserOrgUnit(user_id=member_user.id, org_unit_id=team_b.id, role=None))
    test_db.commit()

    client = _client(test_db, superuser)
    response = client.get(f"/api/admin/users/{member_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert "org_units" in data
    assert len(data["org_units"]) == 2

    by_org_unit_id = {ou["org_unit_id"]: ou for ou in data["org_units"]}
    assert set(by_org_unit_id.keys()) == {team_a.id, team_b.id}
    assert by_org_unit_id[team_a.id]["name"] == "Backend"
    assert by_org_unit_id[team_a.id]["role"] == "Leiter"
    assert by_org_unit_id[team_b.id]["name"] == "Frontend"
    assert by_org_unit_id[team_b.id]["role"] is None


def test_user_detail_includes_org_units_with_memberships(test_db: Session) -> None:
    """Test that org_units field populated with user's org_unit memberships."""
    inst = _make_institution(test_db, slug="admin-user-org-units-memberships")
    superuser = _make_superuser(test_db, inst.id)
    member_user = _make_member_user(test_db, inst.id)
    test_db.flush()

    abteilung = OrgUnit(
        institution_id=inst.id,
        parent_org_unit_id=None,
        unit_type="abteilung",
        name="Informatik",
    )
    test_db.add(abteilung)
    test_db.flush()

    team = OrgUnit(
        institution_id=inst.id,
        parent_org_unit_id=abteilung.id,
        unit_type="team",
        name="Backend",
    )
    test_db.add(team)
    test_db.flush()

    test_db.add(UserOrgUnit(user_id=member_user.id, org_unit_id=team.id, role="Leiter"))
    test_db.commit()

    client = _client(test_db, superuser)
    response = client.get(f"/api/admin/users/{member_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert "org_units" in data
    assert len(data["org_units"]) == 1
    org_unit = data["org_units"][0]
    assert org_unit["org_unit_id"] == team.id
    assert org_unit["name"] == "Backend"
    assert org_unit["unit_type"] == "team"
    assert org_unit["parent_org_unit_id"] == abteilung.id
    assert org_unit["role"] == "Leiter"


def test_user_detail_filters_out_stale_cross_institution_membership(
    test_db: Session,
) -> None:
    """Regression test for the TF-602 review finding.

    A UserOrgUnit row pointing at an OrgUnit belonging to a *different*
    institution than the user's current one (the shape left behind by an
    institution transfer, since transfer_user() only started clearing
    these with this same review fix) must never be surfaced in
    org_units — it would leak a foreign institution's org-unit name/
    hierarchy to whichever admin views this user, and (if it were
    surfaced) render an "Entfernen" button that always 404s, because the
    org-unit lookup behind DELETE /org-units/{id}/members/{user_id} is
    scoped to the *admin's* institution, not the membership's.
    """
    home_inst = _make_institution(test_db, slug="admin-user-org-units-home")
    foreign_inst = _make_institution(test_db, slug="admin-user-org-units-foreign")
    superuser = _make_superuser(test_db, home_inst.id)
    member_user = _make_member_user(test_db, home_inst.id)
    test_db.flush()

    home_unit = OrgUnit(
        institution_id=home_inst.id,
        parent_org_unit_id=None,
        unit_type="abteilung",
        name="Informatik",
    )
    foreign_unit = OrgUnit(
        institution_id=foreign_inst.id,
        parent_org_unit_id=None,
        unit_type="abteilung",
        name="Geheime Abteilung",
    )
    test_db.add_all([home_unit, foreign_unit])
    test_db.flush()

    # Legitimate membership in the user's own institution.
    test_db.add(
        UserOrgUnit(user_id=member_user.id, org_unit_id=home_unit.id, role="Mitglied")
    )
    # Stale membership pointing at a foreign institution's OrgUnit — the
    # shape that could exist if institution_id ever changes without going
    # through transfer_user()'s cleanup (defense-in-depth; see module
    # docstring on _build_org_unit_responses).
    test_db.add(
        UserOrgUnit(user_id=member_user.id, org_unit_id=foreign_unit.id, role=None)
    )
    test_db.commit()

    client = _client(test_db, superuser)
    response = client.get(f"/api/admin/users/{member_user.id}")
    assert response.status_code == 200
    data = response.json()

    org_unit_ids = {ou["org_unit_id"] for ou in data["org_units"]}
    assert org_unit_ids == {home_unit.id}
    assert foreign_unit.id not in org_unit_ids
    names = {ou["name"] for ou in data["org_units"]}
    assert "Geheime Abteilung" not in names


def test_update_user_status_response_includes_org_units(test_db: Session) -> None:
    """Test that a non-get() UserDetailResponse-returning endpoint also carries org_units.

    Regression coverage for the missing `org_units=_build_org_unit_responses(user)` line
    that was found missing on the transfer endpoint's UserDetailResponse construction.
    """
    inst = _make_institution(test_db, slug="admin-user-org-units-status")
    superuser = _make_superuser(test_db, inst.id)
    member_user = _make_member_user(test_db, inst.id)
    test_db.flush()

    abteilung = OrgUnit(
        institution_id=inst.id,
        parent_org_unit_id=None,
        unit_type="abteilung",
        name="Informatik",
    )
    test_db.add(abteilung)
    test_db.flush()

    test_db.add(
        UserOrgUnit(user_id=member_user.id, org_unit_id=abteilung.id, role="Mitglied")
    )
    test_db.commit()

    client = _client(test_db, superuser)
    response = client.patch(
        f"/api/admin/users/{member_user.id}/status",
        json={"status": "inactive"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "org_units" in data
    assert len(data["org_units"]) == 1
    assert data["org_units"][0]["org_unit_id"] == abteilung.id
    assert data["org_units"][0]["role"] == "Mitglied"
