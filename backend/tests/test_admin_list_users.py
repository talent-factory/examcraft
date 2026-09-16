"""
Tests for GET /api/admin/users (list_users), TF-389.

The endpoint had zero coverage despite being the primary admin user
listing — no existing test file exercised it. Covers institution
scoping (superuser vs. regular admin), search/role/status filters,
pagination, and the can_edit flag.
"""

import pytest
from fastapi.testclient import TestClient

from api import admin
from database import get_db
from main import app
from models.auth import Institution, Role, User, UserStatus
from utils.auth_utils import get_current_user


@pytest.fixture
def institution_a(test_db):
    inst = Institution(
        name="Institution A",
        slug="list-users-inst-a",
        subscription_tier="free",
        max_users=100,
        max_documents=50,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.commit()
    test_db.refresh(inst)
    return inst


@pytest.fixture
def institution_b(test_db):
    inst = Institution(
        name="Institution B",
        slug="list-users-inst-b",
        subscription_tier="free",
        max_users=100,
        max_documents=50,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.commit()
    test_db.refresh(inst)
    return inst


@pytest.fixture
def admin_role(test_db):
    role = test_db.query(Role).filter(Role.name == "admin").first()
    if role:
        return role
    role = Role(
        name="admin",
        display_name="Admin",
        description="Institution admin",
        permissions=["manage_users"],
        is_system_role=True,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)
    return role


def _make_user(test_db, institution, email, **overrides):
    defaults = dict(
        email=email,
        password_hash="hashed",
        first_name="Test",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    defaults.update(overrides)
    user = User(**defaults)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def superuser(test_db, institution_a):
    return _make_user(
        test_db, institution_a, "super@list-users.test", is_superuser=True
    )


def _client_as(test_db, user):
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    # Idempotent: avoid appending a duplicate /api/admin/users route on every call.
    if not any(getattr(r, "path", None) == "/api/admin/users" for r in app.routes):
        app.include_router(admin.router)
    return TestClient(app)


class TestListUsersInstitutionScoping:
    def test_superuser_sees_users_from_all_institutions(
        self, test_db, institution_a, institution_b, superuser
    ):
        _make_user(test_db, institution_a, "a1@list-users.test")
        _make_user(test_db, institution_b, "b1@list-users.test")
        client = _client_as(test_db, superuser)

        response = client.get("/api/admin/users?page_size=100")

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["users"]}
        assert "a1@list-users.test" in emails
        assert "b1@list-users.test" in emails

    def test_non_superuser_sees_only_own_institution(
        self, test_db, institution_a, institution_b, admin_role
    ):
        admin_user = _make_user(test_db, institution_a, "admin-a@list-users.test")
        admin_user.roles.append(admin_role)
        test_db.commit()
        _make_user(test_db, institution_a, "a1@list-users.test")
        _make_user(test_db, institution_b, "b1@list-users.test")
        client = _client_as(test_db, admin_user)

        response = client.get("/api/admin/users?page_size=100")

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["users"]}
        assert "a1@list-users.test" in emails
        assert "admin-a@list-users.test" in emails
        assert "b1@list-users.test" not in emails

    def test_superuser_can_filter_by_institution_id(
        self, test_db, institution_a, institution_b, superuser
    ):
        _make_user(test_db, institution_a, "a1@list-users.test")
        _make_user(test_db, institution_b, "b1@list-users.test")
        client = _client_as(test_db, superuser)

        response = client.get(
            f"/api/admin/users?institution_id={institution_b.id}&page_size=100"
        )

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["users"]}
        assert emails == {"b1@list-users.test"}

    def test_non_superuser_institution_id_param_is_ignored(
        self, test_db, institution_a, institution_b, admin_role
    ):
        """Only superusers may cross institutions via `institution_id` — for
        a regular admin the endpoint silently ignores the param and still
        scopes to their own institution (`elif institution_id` in
        `list_users` is only reached once the superuser branch is ruled
        out)."""
        admin_user = _make_user(test_db, institution_a, "admin-a@list-users.test")
        admin_user.roles.append(admin_role)
        test_db.commit()
        _make_user(test_db, institution_a, "a1@list-users.test")
        _make_user(test_db, institution_b, "b1@list-users.test")
        client = _client_as(test_db, admin_user)

        response = client.get(
            f"/api/admin/users?institution_id={institution_b.id}&page_size=100"
        )

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["users"]}
        assert "a1@list-users.test" in emails
        assert "b1@list-users.test" not in emails


class TestListUsersFilters:
    def test_search_filter_matches_email(self, test_db, institution_a, superuser):
        _make_user(test_db, institution_a, "findme@list-users.test")
        _make_user(test_db, institution_a, "other@list-users.test")
        client = _client_as(test_db, superuser)

        response = client.get("/api/admin/users?search=findme")

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["users"]}
        assert emails == {"findme@list-users.test"}

    def test_search_filter_matches_first_name(self, test_db, institution_a, superuser):
        _make_user(
            test_db,
            institution_a,
            "distinctname@list-users.test",
            first_name="Zephyrine",
        )
        client = _client_as(test_db, superuser)

        response = client.get("/api/admin/users?search=Zephyrine")

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["users"]}
        assert "distinctname@list-users.test" in emails

    def test_role_filter(self, test_db, institution_a, admin_role, superuser):
        with_role = _make_user(test_db, institution_a, "hasrole@list-users.test")
        with_role.roles.append(admin_role)
        test_db.commit()
        _make_user(test_db, institution_a, "norole@list-users.test")
        client = _client_as(test_db, superuser)

        response = client.get("/api/admin/users?role=admin")

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["users"]}
        assert "hasrole@list-users.test" in emails
        assert "norole@list-users.test" not in emails

    def test_status_filter(self, test_db, institution_a, superuser):
        _make_user(
            test_db,
            institution_a,
            "inactive@list-users.test",
            status=UserStatus.INACTIVE.value,
        )
        _make_user(
            test_db,
            institution_a,
            "active-status@list-users.test",
            status=UserStatus.ACTIVE.value,
        )
        client = _client_as(test_db, superuser)

        response = client.get(f"/api/admin/users?status={UserStatus.INACTIVE.value}")

        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["users"]}
        assert "inactive@list-users.test" in emails
        assert "active-status@list-users.test" not in emails


class TestListUsersPaginationAndShape:
    def test_pagination_total_pages_calculated(self, test_db, institution_a, superuser):
        for i in range(5):
            _make_user(test_db, institution_a, f"page{i}@list-users.test")
        client = _client_as(test_db, superuser)

        response = client.get("/api/admin/users?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total"] >= 5
        assert data["total_pages"] >= 3

    def test_can_edit_true_for_superuser(self, test_db, institution_a, superuser):
        client = _client_as(test_db, superuser)

        response = client.get("/api/admin/users")

        assert response.status_code == 200
        assert response.json()["can_edit"] is True

    def test_plain_user_without_admin_role_is_forbidden(self, test_db, institution_a):
        """A regular institution member (no admin role, not superuser) must not
        be able to enumerate the institution's user directory via this bulk
        listing endpoint (unlike the single-user detail endpoint)."""
        plain_user = _make_user(test_db, institution_a, "plain@list-users.test")
        client = _client_as(test_db, plain_user)

        response = client.get("/api/admin/users")

        assert response.status_code == 403

    def test_user_item_includes_institution_name_and_roles(
        self, test_db, institution_a, admin_role, superuser
    ):
        user = _make_user(test_db, institution_a, "shaped@list-users.test")
        user.roles.append(admin_role)
        test_db.commit()
        client = _client_as(test_db, superuser)

        response = client.get("/api/admin/users?search=shaped")

        assert response.status_code == 200
        item = response.json()["users"][0]
        assert item["institution_name"] == "Institution A"
        assert "admin" in item["roles"]
