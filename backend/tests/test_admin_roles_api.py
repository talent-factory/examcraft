"""
Tests for Admin Roles API endpoints.

Tests the list_roles endpoint and permission parsing logic, verifying that
roles created via POST /api/admin/roles are correctly returned by GET /api/admin/roles
with their permissions properly parsed from Postgres array literal format.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from models.auth import User, Role, Institution, UserStatus
from utils.auth_utils import get_current_user, get_current_superuser
from utils.permissions import parse_role_permissions as _parse_role_permissions
from database import get_db


def _make_institution(db, slug: str = "test-inst"):
    """Helper to create an institution for testing."""
    inst = Institution(
        name=f"Test Institution {slug}",
        slug=slug,
        domain=f"{slug}.example.com",
        subscription_tier="free",
        max_users=100,
        max_documents=50,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@pytest.fixture
def test_institution(test_db):
    """Create a test institution."""
    institution = Institution(
        name="Test Inst",
        slug="test-inst",
    )
    test_db.add(institution)
    test_db.commit()
    test_db.refresh(institution)
    return institution


@pytest.fixture
def superuser(test_db, test_institution) -> User:
    """Create a superuser for auth."""
    user = User(
        email="super@test.com",
        password_hash="hashed",
        first_name="Super",
        last_name="User",
        institution_id=test_institution.id,
        is_superuser=True,
        is_email_verified=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def non_superuser(test_db):
    """Create a regular (non-superuser) for testing."""
    inst = _make_institution(test_db, "test-inst-regular")

    # Create regular user
    user = User(
        email="user@example.com",
        password_hash="hashed_password",
        first_name="Regular",
        last_name="User",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    return user


@pytest.fixture
def client_superuser(test_db, superuser):
    """TestClient with superuser override."""

    def override_get_current_user():
        return superuser

    def override_get_db():
        return test_db

    # Override both get_current_user and get_db
    # get_current_superuser depends on get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app, raise_server_exceptions=True)
    app.dependency_overrides.clear()


@pytest.fixture
def client_non_superuser(test_db, non_superuser):
    """Create a TestClient with non-superuser dependency override."""
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: non_superuser
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestParseRolePermissions:
    """Test the _parse_role_permissions helper function."""

    def test_parse_json_string(self):
        """Test parsing JSON array format."""
        result = _parse_role_permissions('["perm1", "perm2"]')
        assert result == ["perm1", "perm2"]

    def test_parse_postgres_array_literal(self):
        """Test parsing Postgres array literal format."""
        result = _parse_role_permissions("{perm1,perm2,perm3}")
        assert result == ["perm1", "perm2", "perm3"]

    def test_parse_postgres_array_with_spaces(self):
        """Test parsing Postgres array literal with whitespace."""
        result = _parse_role_permissions("{ perm1 , perm2 , perm3 }")
        assert result == ["perm1", "perm2", "perm3"]

    def test_parse_python_list(self):
        """Test parsing Python list."""
        result = _parse_role_permissions(["perm1", "perm2"])
        assert result == ["perm1", "perm2"]

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = _parse_role_permissions("")
        assert result == []

    def test_parse_none(self):
        """Test parsing None."""
        result = _parse_role_permissions(None)
        assert result == []

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON falls back to array literal check."""
        result = _parse_role_permissions("{invalid json}")
        # Will fall back to array literal, return ["invalid json"]
        assert result == ["invalid json"]

    def test_parse_invalid_format(self):
        """Test parsing completely invalid format."""
        result = _parse_role_permissions("invalid")
        assert result == []


class TestListRolesPermissionsParsing:
    """Test that list_roles correctly parses permissions in all formats.

    This validates the fix for the review finding: _parse_role_permissions
    is now used consistently across all endpoints (list_roles, get_user, update_user)
    to handle JSON, Postgres array literal, and Python list formats.
    """

    def test_list_roles_parses_json_permissions(self, test_db, test_institution):
        """Test that roles with JSON-format permissions are correctly parsed."""
        role = Role(
            name="test_role",
            display_name="Test Role",
            description="A test role",
            permissions='["read", "write"]',  # JSON format
            is_system_role=False,
        )
        test_db.add(role)
        test_db.commit()
        test_db.refresh(role)

        # Call the helper directly to verify parsing
        parsed = _parse_role_permissions(role.permissions)
        assert parsed == ["read", "write"]

    def test_list_roles_parses_postgres_array_permissions(
        self, test_db, test_institution
    ):
        """Test that roles with Postgres array literal format permissions are correctly parsed.

        This is the critical test case that validates the fix for the review finding:
        roles created via POST /api/admin/roles (which assigns permissions as a Python list,
        serialized by psycopg2 as Postgres array literal) should be correctly parsed by
        list_roles using _parse_role_permissions.
        """
        # Simulate what POST /api/admin/roles does: assign permissions as a Python list
        # psycopg2 will serialize this as a Postgres array literal string: {perm1,perm2}
        role = Role(
            name="admin_role",
            display_name="Admin Role",
            description="A role with admin permissions",
            permissions="{admin:read,admin:write,admin:delete}",  # Postgres array literal
            is_system_role=False,
        )
        test_db.add(role)
        test_db.commit()
        test_db.refresh(role)

        # Call the helper directly to verify parsing works for Postgres array format
        parsed = _parse_role_permissions(role.permissions)
        # This is the critical check: permissions should be correctly parsed from Postgres format
        assert parsed == [
            "admin:read",
            "admin:write",
            "admin:delete",
        ]

    def test_list_roles_parses_mixed_permission_formats(
        self, test_db, test_institution
    ):
        """Test that roles with different permission formats are all correctly parsed."""
        # Role 1: JSON format
        role1 = Role(
            name="role_json",
            display_name="JSON Role",
            permissions='["perm1", "perm2"]',
            is_system_role=False,
        )
        # Role 2: Postgres array literal format
        role2 = Role(
            name="role_array",
            display_name="Array Role",
            permissions="{perm3, perm4}",
            is_system_role=False,
        )
        # Role 3: Empty permissions (stored as empty JSON array)
        role3 = Role(
            name="role_empty",
            display_name="Empty Role",
            permissions="[]",  # Empty JSON array
            is_system_role=False,
        )
        test_db.add_all([role1, role2, role3])
        test_db.commit()

        # Verify each role's permissions are correctly parsed
        assert _parse_role_permissions(role1.permissions) == ["perm1", "perm2"]
        assert _parse_role_permissions(role2.permissions) == ["perm3", "perm4"]
        assert _parse_role_permissions(role3.permissions) == []


# ============================================================================
# Restored Tests from Task 2 & Task 3 (Endpoints — accidentally deleted in fix)
# ============================================================================


@pytest.fixture
def regular_user(test_db):
    """Create a regular (non-superuser) for testing — legacy fixture."""
    inst = _make_institution(test_db, "test-inst-legacy")

    # Create regular user
    user = User(
        email="regular@example.com",
        password_hash="hashed_password",
        first_name="Regular",
        last_name="Legacy",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    return user


def test_list_permissions_returns_manage_org_units(test_db, superuser):
    """Test that GET /api/admin/permissions returns manage_org_units."""
    # Setup dependency overrides
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_superuser] = lambda: superuser

    try:
        with TestClient(app) as client:
            response = client.get("/api/admin/permissions")
            assert response.status_code == 200

            data = response.json()
            keys = [perm["key"] for perm in data]
            assert "manage_org_units" in keys
    finally:
        app.dependency_overrides.clear()


def test_list_permissions_requires_superuser(test_db, regular_user):
    """Test that GET /api/admin/permissions requires superuser."""
    # Setup dependency overrides
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: regular_user

    try:
        with TestClient(app) as client:
            response = client.get("/api/admin/permissions")
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_create_role_succeeds(client_superuser, test_db):
    """Test that POST /api/admin/roles creates a role successfully."""
    response = client_superuser.post(
        "/api/admin/roles",
        json={
            "name": "fachbereichsleiter",
            "display_name": "Fachbereichsleiter",
            "description": "Leitet einen Fachbereich",
            "permissions": ["manage_org_units", "review_questions"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "fachbereichsleiter"
    assert set(body["permissions"]) == {"manage_org_units", "review_questions"}
    assert body["is_system_role"] is False

    role = test_db.query(Role).filter(Role.name == "fachbereichsleiter").first()
    assert role is not None


def test_create_role_rejects_unknown_permission(client_superuser):
    """Test that POST /api/admin/roles rejects unknown permissions."""
    response = client_superuser.post(
        "/api/admin/roles",
        json={
            "name": "broken-role",
            "display_name": "Broken",
            "description": None,
            "permissions": ["manage_org_unit"],  # Tippfehler, fehlendes "s"
        },
    )
    assert response.status_code == 422


def test_create_role_rejects_duplicate_name(client_superuser, test_db):
    """Test that POST /api/admin/roles rejects duplicate role names."""
    existing = Role(
        name="dup-role-admroles",
        display_name="Dup",
        permissions='["manage_org_units"]',
        is_system_role=False,
    )
    test_db.add(existing)
    test_db.commit()

    response = client_superuser.post(
        "/api/admin/roles",
        json={
            "name": "dup-role-admroles",
            "display_name": "Duplicate",
            "description": None,
            "permissions": [],
        },
    )
    assert response.status_code == 409


def test_create_role_requires_superuser(client_non_superuser):
    """Test that POST /api/admin/roles requires superuser."""
    response = client_non_superuser.post(
        "/api/admin/roles",
        json={
            "name": "blocked-role",
            "display_name": "Blocked",
            "description": None,
            "permissions": [],
        },
    )
    assert response.status_code == 403


def test_created_role_permission_is_actually_enforced(client_superuser, test_db):
    """Beweist den vollen Kreis, nicht nur dass das Feld gesetzt wurde.

    Role.permissions ist als Column(Text) deklariert, aber seed_roles.py
    weist ihr direkt eine Python-Liste zu — psycopg2 serialisiert das
    implizit als Postgres-Array-Literal-String ("{a,b,c}"), nicht als
    JSON. User.has_permission() hat dafür einen {...}-Fallback nach dem
    primären json.loads()-Versuch (siehe models/auth.py:428-437). Dieser
    Test verifiziert, dass eine über das neue GUI/API erstellte Rolle
    genau diesen bereits bestehenden Enforcement-Pfad tatsächlich
    durchläuft — nicht nur, dass Role.permissions irgendeinen Wert hat.
    """
    inst = _make_institution(test_db, "admroles-enforce")
    response = client_superuser.post(
        "/api/admin/roles",
        json={
            "name": "enforce-check-role",
            "display_name": "Enforce Check",
            "description": None,
            "permissions": ["manage_org_units"],
        },
    )
    assert response.status_code == 201
    role_id = response.json()["id"]

    role = test_db.query(Role).filter(Role.id == role_id).first()
    user = User(
        email="enforce-check@admroles-api.ch",
        first_name="e",
        last_name="c",
        password_hash="x",
        institution_id=inst.id,
        status="active",
        is_superuser=False,
    )
    user.roles.append(role)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("manage_org_units") is True
    assert user.has_permission("manage_settings") is False


# ============================================================================
# New Integration Test (Fix Round 2)
# ============================================================================


def test_created_role_appears_with_permissions_via_list_roles(
    client_superuser, test_db
):
    """Integration test: create role → list roles → verify permissions are present.

    This test verifies that when a role is created via POST /api/admin/roles with
    permissions, it appears in GET /api/admin/roles with the permissions correctly
    populated (not empty). This ensures the _parse_role_permissions fix is working
    end-to-end through the API.
    """
    # Create a role via POST
    create_response = client_superuser.post(
        "/api/admin/roles",
        json={
            "name": "integration-test-role",
            "display_name": "Integration Test Role",
            "description": "Tests role creation and listing with permissions",
            "permissions": ["manage_org_units"],
        },
    )
    assert create_response.status_code == 201
    created_role = create_response.json()
    assert "manage_org_units" in created_role["permissions"]

    # Now list all roles and find the created one
    list_response = client_superuser.get("/api/admin/roles")
    assert list_response.status_code == 200
    roles = list_response.json()

    # Find our created role in the list
    found_role = None
    for role in roles:
        if role["name"] == "integration-test-role":
            found_role = role
            break

    # Verify it was found and has permissions
    assert found_role is not None, "Created role not found in list_roles response"
    assert "permissions" in found_role, "Role missing permissions field"
    assert found_role["permissions"] is not None, "Role permissions is None"
    assert len(found_role["permissions"]) > 0, "Role permissions is empty"
    assert "manage_org_units" in found_role["permissions"], (
        "Expected permission not in role permissions"
    )


def test_role_with_no_permissions_appears_via_list_roles(client_superuser, test_db):
    """Regression test: a role with zero permissions must not crash GET /api/admin/roles.

    An empty permissions list round-trips through Postgres as the array literal
    "{}", which `_parse_role_permissions` used to misparse as a JSON empty
    object (`json.loads("{}") == {}`) instead of falling back to the array-
    literal branch — crashing `RoleResponse` validation ("Input should be a
    valid list"). This covers the practical admin workflow of creating a role
    without permissions or unchecking all permission checkboxes.
    """
    role = Role(
        name="no-permissions-role",
        display_name="No Permissions Role",
        permissions=[],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    list_response = client_superuser.get("/api/admin/roles")
    assert list_response.status_code == 200
    roles = list_response.json()

    found_role = next((r for r in roles if r["name"] == "no-permissions-role"), None)
    assert found_role is not None, "Role with no permissions not found in list_roles"
    assert found_role["permissions"] == []


# ============================================================================
# Task 4: PATCH /api/admin/roles/{role_id} Tests
# ============================================================================


def test_update_role_permissions_succeeds(client_superuser, test_db):
    """Test that PATCH /api/admin/roles/{id} successfully updates permissions."""
    # Create a role to update
    role = Role(
        name="update-test-role",
        display_name="Update Test Role",
        description="A role for testing updates",
        permissions=["manage_org_units"],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    # Update the role's permissions
    response = client_superuser.patch(
        f"/api/admin/roles/{role.id}",
        json={"permissions": ["manage_org_units", "manage_settings"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["permissions"]) == {"manage_org_units", "manage_settings"}

    # Verify in database
    test_db.refresh(role)
    parsed_permissions = _parse_role_permissions(role.permissions)
    assert set(parsed_permissions) == {"manage_org_units", "manage_settings"}


def test_update_role_permissions_on_system_role_succeeds(client_superuser, test_db):
    """A system role's permissions stay editable — that's the actual point of
    TF-603 (see RolePermissionsEditor.tsx). Only *deleting* a system role is
    forbidden (test_delete_system_role_returns_409); editing its permissions
    must succeed, unlike the sibling test above this only exercises a
    non-system role.

    Uses a role name distinct from the app's own seeded system roles
    (admin/dozent/assistant/viewer, unique-indexed) to avoid colliding with
    rows seeded by main.py's startup lifespan into the same test database.
    """
    role = Role(
        name="update-system-test-role",
        display_name="System Test Role",
        description="System role",
        permissions=["manage_org_units"],
        is_system_role=True,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client_superuser.patch(
        f"/api/admin/roles/{role.id}",
        json={"permissions": ["manage_org_units", "manage_settings"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_system_role"] is True
    assert set(body["permissions"]) == {"manage_org_units", "manage_settings"}

    test_db.refresh(role)
    assert role.is_system_role is True
    parsed_permissions = _parse_role_permissions(role.permissions)
    assert set(parsed_permissions) == {"manage_org_units", "manage_settings"}


def test_update_role_rejects_unknown_permission(client_superuser, test_db):
    """Test that PATCH /api/admin/roles/{id} rejects unknown permissions."""
    role = Role(
        name="update-target-admroles",
        display_name="Target",
        permissions=["manage_org_units"],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client_superuser.patch(
        f"/api/admin/roles/{role.id}",
        json={"permissions": ["not_a_real_permission"]},
    )
    assert response.status_code == 422


def test_update_nonexistent_role_returns_404(client_superuser, test_db):
    """Test that PATCH /api/admin/roles/{id} returns 404 for nonexistent role."""
    response = client_superuser.patch(
        "/api/admin/roles/99999",
        json={"permissions": ["manage_org_units"]},
    )
    assert response.status_code == 404


def test_update_role_partial_updates_display_name(client_superuser, test_db):
    """Test that PATCH /api/admin/roles/{id} can update display_name only."""
    role = Role(
        name="partial-update-role",
        display_name="Old Name",
        description="Original description",
        permissions=["manage_org_units"],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client_superuser.patch(
        f"/api/admin/roles/{role.id}",
        json={"display_name": "New Name"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "New Name"
    assert body["description"] == "Original description"
    assert body["permissions"] == ["manage_org_units"]

    # Verify in database
    test_db.refresh(role)
    assert role.display_name == "New Name"


def test_update_role_partial_updates_description(client_superuser, test_db):
    """Test that PATCH /api/admin/roles/{id} can update description only."""
    role = Role(
        name="partial-desc-role",
        display_name="Display",
        description="Old description",
        permissions=["manage_settings"],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client_superuser.patch(
        f"/api/admin/roles/{role.id}",
        json={"description": "New description"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "New description"
    assert body["display_name"] == "Display"
    assert body["permissions"] == ["manage_settings"]


def test_update_role_requires_superuser(client_non_superuser, test_db):
    """Test that PATCH /api/admin/roles/{id} requires superuser."""
    role = Role(
        name="superuser-check-role",
        display_name="Superuser Check",
        permissions=["manage_org_units"],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client_non_superuser.patch(
        f"/api/admin/roles/{role.id}",
        json={"display_name": "Attempted Update"},
    )
    assert response.status_code == 403


# ============================================================================
# Task 5: DELETE /api/admin/roles/{role_id} Tests
# ============================================================================


def test_delete_role_succeeds(client_superuser, test_db):
    """Test that DELETE /api/admin/roles/{id} successfully deletes a role."""
    role = Role(
        name="delete-target-admroles",
        display_name="Delete Target",
        permissions=[],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    role_id = role.id

    response = client_superuser.delete(f"/api/admin/roles/{role_id}")
    assert response.status_code == 204
    assert test_db.query(Role).filter(Role.id == role_id).first() is None


def test_delete_system_role_returns_409(client_superuser, test_db):
    """Test that DELETE /api/admin/roles/{id} returns 409 for system roles."""
    role = Role(
        name="system-role-admroles",
        display_name="System Role",
        permissions=[],
        is_system_role=True,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client_superuser.delete(f"/api/admin/roles/{role.id}")
    assert response.status_code == 409


def test_delete_role_with_assigned_user_returns_409(client_superuser, test_db):
    """Test that DELETE /api/admin/roles/{id} returns 409 if role has assigned users."""
    inst = _make_institution(test_db, "admroles-del-assigned")
    role = Role(
        name="assigned-role-admroles",
        display_name="Assigned",
        permissions=[],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.flush()

    user = User(
        email="assignee@admroles-api.ch",
        first_name="a",
        last_name="s",
        password_hash="x",
        institution_id=inst.id,
        status="active",
        is_superuser=False,
    )
    user.roles.append(role)
    test_db.add(user)
    test_db.commit()

    response = client_superuser.delete(f"/api/admin/roles/{role.id}")
    assert response.status_code == 409


def test_delete_role_requires_superuser(client_non_superuser, test_db):
    """Test that DELETE /api/admin/roles/{id} requires superuser."""
    role = Role(
        name="delete-superuser-check-admroles",
        display_name="Delete Superuser Check",
        permissions=[],
        is_system_role=False,
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)

    response = client_non_superuser.delete(f"/api/admin/roles/{role.id}")
    assert response.status_code == 403
    assert test_db.query(Role).filter(Role.id == role.id).first() is not None


def test_delete_nonexistent_role_returns_404(client_superuser, test_db):
    """Test that DELETE /api/admin/roles/{id} returns 404 for a nonexistent role."""
    response = client_superuser.delete("/api/admin/roles/99999")
    assert response.status_code == 404
