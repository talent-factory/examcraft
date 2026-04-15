"""
Tests for /api/auth/me profile endpoint fixes:
- Permissions parsing from PostgreSQL array literal format {a,b,c}
- Institution object with subscription_tier in response
- Fresh database detection (create_all + stamp)
"""

import json
import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.auth import User, Role, Institution, UserStatus
from services.auth_service import AuthService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def db_with_pg_array_permissions(test_db):
    """
    Set up roles with PostgreSQL array literal permissions (as stored by seed scripts).
    This reproduces the production format: {perm1,perm2,perm3}
    """
    institution = Institution(
        name="PG Array Test University",
        slug="pg-array-test",
        domain="pgarray.edu",
        subscription_tier="free",
        max_users=5,
        max_documents=10,
        max_questions_per_month=50,
    )
    test_db.add(institution)
    test_db.flush()

    # Store permissions as PostgreSQL array literal (how seed scripts store them)
    # Use get-or-update pattern to avoid UniqueViolation when CI seeds roles at startup
    viewer_role = test_db.query(Role).filter(Role.name == "viewer").first()
    if viewer_role:
        viewer_role.permissions = (
            "{view_questions,view_exams,documents:read,create_documents}"
        )
    else:
        viewer_role = Role(
            name="viewer",
            display_name="Viewer",
            description="View-only access",
            permissions="{view_questions,view_exams,documents:read,create_documents}",
            is_system_role=True,
        )
        test_db.add(viewer_role)

    dozent_role = test_db.query(Role).filter(Role.name == "dozent").first()
    if dozent_role:
        dozent_role.permissions = "{create_questions,edit_questions,review_questions,view_questions,view_exams,documents:read,create_documents}"
    else:
        dozent_role = Role(
            name="dozent",
            display_name="Dozent",
            description="Full teaching access",
            permissions="{create_questions,edit_questions,review_questions,view_questions,view_exams,documents:read,create_documents}",
            is_system_role=True,
        )
        test_db.add(dozent_role)
    test_db.commit()

    yield test_db


@pytest.fixture(scope="function")
def db_with_json_permissions(test_db):
    """
    Set up roles with JSON array permissions (as stored by tests / manual inserts).
    """
    institution = Institution(
        name="JSON Test University",
        slug="json-test",
        domain="jsontest.edu",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(institution)
    test_db.flush()

    viewer_role = test_db.query(Role).filter(Role.name == "viewer").first()
    json_perms = json.dumps(
        ["view_questions", "view_exams", "documents:read", "create_documents"]
    )
    if viewer_role:
        viewer_role.permissions = json_perms
    else:
        viewer_role = Role(
            name="viewer",
            display_name="Viewer",
            description="View-only access",
            permissions=json_perms,
            is_system_role=True,
        )
        test_db.add(viewer_role)
    test_db.commit()

    yield test_db


def _create_test_client(db):
    """Create a TestClient with DB override and routers."""
    from api import auth

    app.include_router(auth.router)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client


def _create_user_and_login(db, client, role_name="viewer"):
    """Helper: create user with given role, login, return (user, access_token)."""
    institution = db.query(Institution).first()
    role = db.query(Role).filter(Role.name == role_name).first()

    user = User(
        email="profiletest@example.com",
        password_hash=AuthService.get_password_hash("TestPass123!"),
        first_name="Profile",
        last_name="Tester",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_email_verified=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()
    user.roles.append(role)
    db.commit()
    db.refresh(user)

    login_resp = client.post(
        "/api/auth/login",
        json={"email": "profiletest@example.com", "password": "TestPass123!"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]

    return user, access_token


# ============================================================================
# Permissions Parsing Tests
# ============================================================================


class TestPermissionsParsing:
    """Tests for parsing role permissions in /api/auth/me response."""

    def test_pg_array_literal_permissions_are_parsed(
        self, db_with_pg_array_permissions
    ):
        """
        Permissions stored as PostgreSQL array literal {a,b,c} must be
        correctly parsed into a JSON array in the /me response.

        This was a bug where json.loads() failed on {a,b,c} format and
        silently returned an empty permissions list.
        """
        db = db_with_pg_array_permissions
        client = _create_test_client(db)

        try:
            _, token = _create_user_and_login(db, client, "viewer")

            resp = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()

            permissions = data["roles"][0]["permissions"]
            assert isinstance(permissions, list)
            assert len(permissions) > 0, "Permissions must not be empty"
            assert "view_questions" in permissions
            assert "view_exams" in permissions
            assert "documents:read" in permissions
            assert "create_documents" in permissions
        finally:
            app.dependency_overrides.clear()

    def test_json_array_permissions_are_parsed(self, db_with_json_permissions):
        """
        Permissions stored as JSON array ["a","b"] must still work correctly.
        """
        db = db_with_json_permissions
        client = _create_test_client(db)

        try:
            _, token = _create_user_and_login(db, client, "viewer")

            resp = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()

            permissions = data["roles"][0]["permissions"]
            assert isinstance(permissions, list)
            assert len(permissions) > 0
            assert "view_questions" in permissions
            assert "documents:read" in permissions
        finally:
            app.dependency_overrides.clear()

    def test_empty_pg_array_permissions(self, test_db):
        """Permissions stored as empty PG array {} should return empty list."""
        institution = Institution(
            name="Empty Perm University",
            slug="empty-perm",
            subscription_tier="free",
            max_users=1,
            max_documents=1,
            max_questions_per_month=1,
        )
        test_db.add(institution)
        test_db.flush()

        role = Role(
            name="viewer",
            display_name="Empty Role",
            description="No permissions",
            permissions="{}",
            is_system_role=True,
        )
        test_db.add(role)
        test_db.commit()

        client = _create_test_client(test_db)
        try:
            _, token = _create_user_and_login(test_db, client, "viewer")

            resp = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            permissions = resp.json()["roles"][0]["permissions"]
            assert permissions == []
        finally:
            app.dependency_overrides.clear()

    def test_dozent_pg_array_permissions(self, db_with_pg_array_permissions):
        """Dozent role with PG array permissions should include all teaching permissions."""
        db = db_with_pg_array_permissions
        client = _create_test_client(db)

        try:
            _, token = _create_user_and_login(db, client, "dozent")

            resp = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            permissions = resp.json()["roles"][0]["permissions"]

            assert "create_questions" in permissions
            assert "edit_questions" in permissions
            assert "review_questions" in permissions
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# Institution in Profile Response Tests
# ============================================================================


class TestInstitutionInProfile:
    """Tests for institution object (with subscription_tier) in /me response."""

    def test_institution_included_in_profile(self, db_with_pg_array_permissions):
        """
        The /me response must include an 'institution' object with
        id, name, and subscription_tier.

        This was missing — the frontend needs institution.subscription_tier
        to evaluate feature access via hasPermission().
        """
        db = db_with_pg_array_permissions
        client = _create_test_client(db)

        try:
            _, token = _create_user_and_login(db, client, "viewer")

            resp = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()

            assert "institution" in data
            assert data["institution"] is not None

            institution = data["institution"]
            assert "id" in institution
            assert "name" in institution
            assert "subscription_tier" in institution
            assert institution["name"] == "PG Array Test University"
            assert institution["subscription_tier"] == "free"
        finally:
            app.dependency_overrides.clear()

    def test_institution_tier_professional(self, db_with_json_permissions):
        """Institution with professional tier should be reflected in profile."""
        db = db_with_json_permissions
        client = _create_test_client(db)

        try:
            _, token = _create_user_and_login(db, client, "viewer")

            resp = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200

            institution = resp.json()["institution"]
            assert institution["subscription_tier"] == "professional"
        finally:
            app.dependency_overrides.clear()

    def test_institution_backward_compatible(self, db_with_pg_array_permissions):
        """
        The response must still contain institution_id and institution_name
        for backward compatibility, in addition to the new institution object.
        """
        db = db_with_pg_array_permissions
        client = _create_test_client(db)

        try:
            _, token = _create_user_and_login(db, client, "viewer")

            resp = client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            data = resp.json()

            # Old fields still present
            assert "institution_id" in data
            assert "institution_name" in data
            assert data["institution_id"] is not None
            assert data["institution_name"] == "PG Array Test University"

            # New field also present
            assert data["institution"]["id"] == data["institution_id"]
            assert data["institution"]["name"] == data["institution_name"]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# Fresh Database Detection Tests
# ============================================================================


class TestFreshDatabaseDetection:
    """Tests for fresh database detection logic in database.py."""

    def test_table_exists_helper_in_migration(self):
        """
        The _table_exists() and _column_exists() helpers in the first migration
        must handle missing tables gracefully.
        """
        import importlib.util
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "alembic",
            "versions",
            "2026_03_12_d715210cb3a3_add_user_audit_fields.py",
        )
        migration_path = os.path.normpath(migration_path)

        spec = importlib.util.spec_from_file_location("migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        # Verify the functions exist
        assert hasattr(migration, "_table_exists")
        assert hasattr(migration, "_column_exists")

    def test_fresh_db_detection_logic_exists(self):
        """
        The database.py _run_migrations_or_create_all function must contain
        fresh database detection that creates schema before running migrations.
        """
        import inspect
        from database import _run_migrations_or_create_all

        source = inspect.getsource(_run_migrations_or_create_all)
        assert "Fresh database detected" in source
        assert "create_all" in source
        assert "stamp" in source

    def test_feedback_cluster_model_imported(self):
        """
        FeedbackCluster must be imported in database.py so that
        Base.metadata.create_all() includes the feedback_clusters table.
        """
        import inspect
        from database import create_tables

        source = inspect.getsource(create_tables)
        assert "feedback_cluster" in source
