"""
Tests for Role-Based Access Control (RBAC)
Tests permissions, roles, and access control
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.auth import User, Role, Institution, UserStatus
from services.auth_service import AuthService
from tests.conftest import login_headers

# Own role names instead of the seeded admin/dozent/viewer: a get-or-create on
# the real names would silently test whatever permissions an earlier test or
# seed left behind.
DOZENT_ROLE = "test_rbac_dozent"
ASSISTANT_ROLE = "test_rbac_assistant"
VIEWER_ROLE = "test_rbac_viewer"


@pytest.fixture(scope="function")
def db(test_db):
    """Use PostgreSQL test database from conftest.py"""
    institution = Institution(
        name="Test University",
        slug="test-university",
        domain="test.edu",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(institution)
    test_db.flush()

    test_db.add_all(
        [
            Role(
                name=DOZENT_ROLE,
                display_name="Dozent",
                description="Can create and review questions",
                permissions=[
                    "create_questions",
                    "review_questions",
                    "edit_questions",
                    "create_documents",
                    "delete_documents",
                    "view_questions",
                ],
            ),
            Role(
                name=ASSISTANT_ROLE,
                display_name="Assistant",
                description="Can create questions",
                permissions=["create_questions", "create_documents", "view_questions"],
            ),
            Role(
                name=VIEWER_ROLE,
                display_name="Viewer",
                description="Can view questions",
                permissions=["view_questions"],
            ),
        ]
    )
    test_db.commit()

    yield test_db


@pytest.fixture(scope="function")
def test_client(db):
    """Create test client with database override.

    ``with`` runs the app lifespan, which registers the routers; a bare
    ``TestClient(app)`` answers every API route with 404.
    """

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client


def create_user_with_role(db, email: str, role_name: str):
    """Helper to create user with specific role"""
    institution = db.query(Institution).filter_by(slug="test-university").one()
    role = db.query(Role).filter(Role.name == role_name).one()

    user = User(
        email=email,
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="Test",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    user.roles.append(role)
    db.commit()
    db.refresh(user)

    return user


# ============================================================================
# Permission Tests
# ============================================================================


def test_dozent_has_specific_permissions(db):
    """Test that dozent role has specific permissions"""
    user = create_user_with_role(db, "dozent@test.com", DOZENT_ROLE)

    # Dozent should have these permissions
    assert user.has_permission("create_questions")
    assert user.has_permission("review_questions")
    assert user.has_permission("create_documents")

    # Dozent should NOT have admin permissions
    assert not user.has_permission("delete_users")


def test_viewer_has_limited_permissions(db):
    """Test that viewer role has limited permissions"""
    user = create_user_with_role(db, "viewer@test.com", VIEWER_ROLE)

    # Viewer should only have view permission
    assert user.has_permission("view_questions")

    # Viewer should NOT have create/edit permissions
    assert not user.has_permission("create_questions")
    assert not user.has_permission("review_questions")
    assert not user.has_permission("create_documents")


# ============================================================================
# API Access Control Tests
# ============================================================================


def test_viewer_cannot_create_document(test_client, db):
    """Test that viewer cannot upload documents"""
    create_user_with_role(db, "viewer@test.com", VIEWER_ROLE)
    headers = login_headers(test_client, "viewer@test.com", "testpassword123")

    response = test_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("test.txt", b"test content", "text/plain")},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "auth_permission_required"


def test_dozent_can_create_document(test_client, db):
    """Test that dozent passes the permission check of the upload endpoint"""
    create_user_with_role(db, "dozent@test.com", DOZENT_ROLE)
    headers = login_headers(test_client, "dozent@test.com", "testpassword123")

    # visibility=team without org_unit_id is rejected right after the
    # permission check, before the file system or Celery get involved.
    response = test_client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("test.txt", b"test content", "text/plain")},
        data={"visibility": "team"},
    )

    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "documents_visibility_invalid_org_unit"


def test_viewer_cannot_approve_question(test_client, db):
    """Test that viewer cannot approve questions"""
    create_user_with_role(db, "viewer@test.com", VIEWER_ROLE)
    headers = login_headers(test_client, "viewer@test.com", "testpassword123")

    response = test_client.post(
        "/api/v1/questions/1/approve",
        headers=headers,
        json={"reason": "Looks good"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "auth_permission_required"


def test_dozent_can_approve_question(test_client, db):
    """Test that dozent passes the permission check of the approve endpoint"""
    create_user_with_role(db, "dozent@test.com", DOZENT_ROLE)
    headers = login_headers(test_client, "dozent@test.com", "testpassword123")

    response = test_client.post(
        "/api/v1/questions/999999999/approve",
        headers=headers,
        json={"reason": "Looks good"},
    )

    # The question does not exist: past the permission check, the lookup fails
    assert response.status_code == 404, response.text


# ============================================================================
# Multi-Role Tests
# ============================================================================


def test_user_with_multiple_roles(db):
    """Test user with multiple roles has combined permissions"""
    user = create_user_with_role(db, "multi@test.com", VIEWER_ROLE)
    user.roles.append(db.query(Role).filter(Role.name == ASSISTANT_ROLE).one())
    db.commit()
    db.refresh(user)

    # Should have permissions from both roles
    assert user.has_permission("view_questions")  # From viewer
    assert user.has_permission("create_questions")  # From assistant
    assert user.has_permission("create_documents")  # From assistant
    assert not user.has_permission("review_questions")  # From neither


# ============================================================================
# Superuser Tests
# ============================================================================


def test_superuser_has_all_permissions(db):
    """Test that superuser has all permissions regardless of roles"""
    institution = db.query(Institution).filter_by(slug="test-university").one()

    user = User(
        email="superuser@test.com",
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="Super",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,  # Superuser flag
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Superuser should have any permission even without roles
    assert user.has_permission("create_questions")
    assert user.has_permission("delete_users")
    assert user.has_permission("any_permission")
