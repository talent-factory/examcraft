"""
Tests for Auth API Endpoints
Tests registration, login, logout, password change, etc.
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

    # Create default roles
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
                "create_documents",
                "view_questions",
            ],
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


@pytest.fixture
def test_user(db):
    """Create a test user"""
    institution = db.query(Institution).first()
    viewer_role = db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()

    user = User(
        email="test@example.com",
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="Test",
        last_name="User",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    user.roles.append(viewer_role)
    db.commit()
    db.refresh(user)

    return user


# ============================================================================
# Registration Tests
# ============================================================================


def test_register_new_user(test_client, db):
    """Test successful user registration"""
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Verify user was created
    user = db.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.first_name == "New"
    assert user.last_name == "User"
    assert user.status == UserStatus.ACTIVE.value

    # Verify user has viewer role
    assert len(user.roles) == 1
    assert user.roles[0].name == UserRole.VIEWER.value


def test_register_duplicate_email(test_client, test_user):
    """Test registration with existing email fails"""
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": "Duplicate",
            "last_name": "User",
        },
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_register_invalid_email(client):
    """Test registration with invalid email fails"""
    response = test_client.post(
        "/api/auth/register",
        json={
            "email": "invalid-email",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )

    assert response.status_code == 422  # Validation error


# ============================================================================
# Login Tests
# ============================================================================


def test_login_success(test_client, test_user):
    """Test successful login"""
    response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(test_client, test_user):
    """Test login with wrong password fails"""
    response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client):
    """Test login with non-existent user fails"""
    response = test_client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_inactive_user(test_client, db, test_user):
    """Test login with inactive user fails"""
    test_user.status = UserStatus.INACTIVE.value
    db.commit()

    response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


# ============================================================================
# Token Refresh Tests
# ============================================================================


def test_refresh_token_success(test_client, test_user):
    """Test successful token refresh"""
    # Login to get tokens
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = test_client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_token_invalid(client):
    """Test refresh with invalid token fails"""
    response = test_client.post(
        "/api/auth/refresh", json={"refresh_token": "invalid.token.here"}
    )

    assert response.status_code == 401


# ============================================================================
# Logout Tests
# ============================================================================


def test_logout_success(test_client, test_user):
    """Test successful logout"""
    # Login first
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    access_token = login_response.json()["access_token"]

    # Logout
    response = test_client.post(
        "/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 204


def test_logout_without_token(client):
    """Test logout without token fails"""
    response = test_client.post("/api/auth/logout")

    assert response.status_code == 403  # No credentials


# ============================================================================
# User Profile Tests
# ============================================================================


def test_get_profile_success(test_client, test_user):
    """Test getting current user profile"""
    # Login first
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    access_token = login_response.json()["access_token"]

    # Get profile
    response = test_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert "roles" in data


# ============================================================================
# Password Change Tests
# ============================================================================


def test_change_password_success(test_client, test_user, db):
    """Test successful password change"""
    # Login first
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    access_token = login_response.json()["access_token"]

    # Change password
    response = test_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "testpassword123",
            "new_password": "NewSecurePass456!",
        },
    )

    assert response.status_code == 204

    # Verify new password works
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "NewSecurePass456!"},
    )
    assert login_response.status_code == 200


def test_change_password_wrong_current(test_client, test_user):
    """Test password change with wrong current password fails"""
    # Login first
    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    access_token = login_response.json()["access_token"]

    # Try to change password with wrong current password
    response = test_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current_password": "wrongpassword", "new_password": "NewSecurePass456!"},
    )

    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


def test_change_password_without_auth(client):
    """Test password change without authentication fails"""
    response = test_client.post(
        "/api/auth/change-password",
        json={
            "current_password": "testpassword123",
            "new_password": "NewSecurePass456!",
        },
    )

    assert response.status_code == 403  # No credentials
