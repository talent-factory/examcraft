"""
Tests for Role-Based Access Control (RBAC)
Tests permissions, roles, and access control
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from database import get_db
from models.auth import User, Role, Institution, UserStatus, UserRole
from services.auth_service import AuthService


@pytest.fixture(scope="function")
def db(test_db):
    """Use PostgreSQL test database from conftest.py"""
    # Create test institution
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

    # Create roles with different permissions
    roles = [
        Role(
            name=UserRole.ADMIN.value,
            display_name="Admin",
            description="Full system access",
            permissions=["*"],
            is_system_role=True,
        ),
        Role(
            name=UserRole.DOZENT.value,
            display_name="Dozent",
            description="Can create and manage questions",
            permissions=[
                "create_questions",
                "approve_questions",
                "edit_questions",
                "create_documents",
                "delete_documents",
                "view_questions",
            ],
            is_system_role=True,
        ),
        Role(
            name=UserRole.ASSISTANT.value,
            display_name="Assistant",
            description="Can create questions",
            permissions=["create_questions", "create_documents", "view_questions"],
            is_system_role=True,
        ),
        Role(
            name=UserRole.VIEWER.value,
            display_name="Viewer",
            description="Can view questions",
            permissions=["view_questions"],
            is_system_role=True,
        ),
    ]
    for role in roles:
        test_db.add(role)

    test_db.commit()

    yield test_db


@pytest.fixture(scope="function")
def test_client(db):
    """Create test client with database override"""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def create_user_with_role(db, email: str, role_name: str):
    """Helper to create user with specific role"""
    institution = db.query(Institution).first()
    role = db.query(Role).filter(Role.name == role_name).first()

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


def get_auth_token(test_client, email: str):
    """Helper to get auth token for user"""
    response = test_client.post(
        "/api/auth/login", json={"email": email, "password": "testpassword123"}
    )
    return response.json()["access_token"]


# ============================================================================
# Permission Tests
# ============================================================================


def test_admin_has_all_permissions(db):
    """Test that admin role has wildcard permission"""
    db.query(Role).filter(Role.name == UserRole.ADMIN.value).first()
    user = create_user_with_role(db, "admin@test.com", UserRole.ADMIN.value)

    # Admin should have any permission
    assert user.has_permission("create_questions")
    assert user.has_permission("delete_documents")
    assert user.has_permission("any_permission")


def test_dozent_has_specific_permissions(db):
    """Test that dozent role has specific permissions"""
    user = create_user_with_role(db, "dozent@test.com", UserRole.DOZENT.value)

    # Dozent should have these permissions
    assert user.has_permission("create_questions")
    assert user.has_permission("approve_questions")
    assert user.has_permission("create_documents")

    # Dozent should NOT have admin permissions
    assert not user.has_permission("delete_users")


def test_viewer_has_limited_permissions(db):
    """Test that viewer role has limited permissions"""
    user = create_user_with_role(db, "viewer@test.com", UserRole.VIEWER.value)

    # Viewer should only have view permission
    assert user.has_permission("view_questions")

    # Viewer should NOT have create/edit permissions
    assert not user.has_permission("create_questions")
    assert not user.has_permission("approve_questions")
    assert not user.has_permission("create_documents")


# ============================================================================
# API Access Control Tests
# ============================================================================


def test_viewer_cannot_create_document(test_client, db):
    """Test that viewer cannot upload documents"""
    create_user_with_role(db, "viewer@test.com", UserRole.VIEWER.value)
    token = get_auth_token(test_client, "viewer@test.com")

    # Try to upload document
    response = test_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", b"test content", "text/plain")},
    )

    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_dozent_can_create_document(test_client, db):
    """Test that dozent can upload documents"""
    create_user_with_role(db, "dozent@test.com", UserRole.DOZENT.value)
    token = get_auth_token(test_client, "dozent@test.com")

    # Upload document
    response = test_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", b"test content", "text/plain")},
    )

    # Should succeed (201) or fail for other reasons, but NOT 403
    assert response.status_code != 403


def test_viewer_cannot_approve_question(test_client, db):
    """Test that viewer cannot approve questions"""
    create_user_with_role(db, "viewer@test.com", UserRole.VIEWER.value)
    token = get_auth_token(test_client, "viewer@test.com")

    # Try to approve question
    response = test_client.post(
        "/api/v1/questions/1/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Looks good"},
    )

    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_dozent_can_approve_question(test_client, db):
    """Test that dozent can approve questions"""
    create_user_with_role(db, "dozent@test.com", UserRole.DOZENT.value)
    token = get_auth_token(test_client, "dozent@test.com")

    # Try to approve question (will fail with 404 since question doesn't exist, but NOT 403)
    response = test_client.post(
        "/api/v1/questions/1/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Looks good"},
    )

    # Should fail with 404 (not found), NOT 403 (forbidden)
    assert response.status_code != 403


# ============================================================================
# Multi-Role Tests
# ============================================================================


def test_user_with_multiple_roles(db):
    """Test user with multiple roles has combined permissions"""
    institution = db.query(Institution).first()
    viewer_role = db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()
    assistant_role = (
        db.query(Role).filter(Role.name == UserRole.ASSISTANT.value).first()
    )

    user = User(
        email="multi@test.com",
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="Multi",
        last_name="Role",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    # Assign multiple roles
    user.roles.append(viewer_role)
    user.roles.append(assistant_role)
    db.commit()
    db.refresh(user)

    # Should have permissions from both roles
    assert user.has_permission("view_questions")  # From viewer
    assert user.has_permission("create_questions")  # From assistant
    assert user.has_permission("create_documents")  # From assistant


# ============================================================================
# Superuser Tests
# ============================================================================


def test_superuser_has_all_permissions(db):
    """Test that superuser has all permissions regardless of roles"""
    institution = db.query(Institution).first()

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
