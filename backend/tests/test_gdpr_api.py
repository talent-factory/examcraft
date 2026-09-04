"""
Tests für GDPR Compliance API Endpoints (TF-745)

Smoke-Tests für Router-Registrierung + echte HTTP-Flow-Regressionstests für
alle vier Endpunkte. Vor TF-745 lieferten /export-data, /request-deletion,
/cancel-deletion und /delete-account-now durchgehend HTTP 500, weil
``audit_service.log_action`` fälschlich mit ``await`` und dem falschen
Kwarg-Namen ``details=`` statt ``additional_data=`` aufgerufen wurde
(``AuditService.log_action`` ist eine synchrone ``@staticmethod``).
``/delete-account-now`` war zusätzlich durch ``current_user.hashed_password``
kaputt (das Attribut heisst ``password_hash``).
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from services.auth_service import AuthService

client = TestClient(app)


class TestGDPREndpoints:
    """Test GDPR API Endpoints"""

    def test_gdpr_module_imports(self):
        """Test that GDPR module can be imported"""
        try:
            from api import gdpr

            assert gdpr.router is not None
            assert gdpr.router.prefix == "/api/v1/gdpr"
        except ImportError as e:
            pytest.fail(f"Failed to import GDPR module: {e}")

    def test_gdpr_router_has_routes(self):
        """Test that GDPR router has routes defined"""
        from api import gdpr

        # Check that router has routes
        assert len(gdpr.router.routes) > 0

        # Check for expected routes (with full prefix)
        route_paths = [route.path for route in gdpr.router.routes]
        assert "/api/v1/gdpr/export-data" in route_paths
        assert "/api/v1/gdpr/request-deletion" in route_paths
        assert "/api/v1/gdpr/cancel-deletion" in route_paths
        assert "/api/v1/gdpr/delete-account-now" in route_paths

    def test_gdpr_endpoints_require_authentication(self):
        """Test that GDPR endpoints are protected"""
        from api import gdpr

        # All routes should require authentication (have dependencies)
        for route in gdpr.router.routes:
            # Check if route has dependencies (authentication)
            if hasattr(route, "dependant"):
                # Routes with dependencies are protected
                assert route.dependant is not None


# ============================================================================
# HTTP-Flow-Regressionstests (TF-745)
# ============================================================================


@pytest.fixture(scope="function")
def db(test_db):
    institution = Institution(
        name="GDPR API Test Institution",
        slug="gdpr-api-test-institution",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(institution)
    test_db.commit()
    yield test_db


@pytest.fixture(scope="function")
def test_client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    from api import auth, gdpr

    app.include_router(auth.router)
    app.include_router(gdpr.router)
    app.dependency_overrides[get_db] = override_get_db
    api_client = TestClient(app)
    yield api_client
    app.dependency_overrides.clear()


@pytest.fixture
def gdpr_test_user(db):
    institution = db.query(Institution).first()
    user = User(
        email="gdpr-flow@gdpr-api-test-institution.ch",
        password_hash=AuthService.get_password_hash("testpassword123"),
        first_name="GDPR",
        last_name="Flow",
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login_headers(test_client, email: str, password: str) -> dict:
    response = test_client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_export_data_returns_200(test_client, gdpr_test_user):
    headers = _login_headers(test_client, gdpr_test_user.email, "testpassword123")

    response = test_client.get("/api/v1/gdpr/export-data", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_profile"]["email"] == gdpr_test_user.email


def test_request_deletion_returns_200_and_sets_schedule(test_client, gdpr_test_user):
    headers = _login_headers(test_client, gdpr_test_user.email, "testpassword123")

    response = test_client.post("/api/v1/gdpr/request-deletion", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["grace_period_days"] == 30
    assert "deletion_date" in data


def test_request_deletion_twice_returns_400(test_client, gdpr_test_user):
    headers = _login_headers(test_client, gdpr_test_user.email, "testpassword123")

    first = test_client.post("/api/v1/gdpr/request-deletion", headers=headers)
    assert first.status_code == 200

    second = test_client.post("/api/v1/gdpr/request-deletion", headers=headers)
    assert second.status_code == 400


def test_cancel_deletion_returns_200(test_client, gdpr_test_user):
    headers = _login_headers(test_client, gdpr_test_user.email, "testpassword123")
    test_client.post("/api/v1/gdpr/request-deletion", headers=headers)

    response = test_client.post("/api/v1/gdpr/cancel-deletion", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_cancel_deletion_without_pending_returns_400(test_client, gdpr_test_user):
    headers = _login_headers(test_client, gdpr_test_user.email, "testpassword123")

    response = test_client.post("/api/v1/gdpr/cancel-deletion", headers=headers)

    assert response.status_code == 400


def test_delete_account_now_wrong_password_returns_401(test_client, gdpr_test_user):
    headers = _login_headers(test_client, gdpr_test_user.email, "testpassword123")

    response = test_client.request(
        "DELETE",
        "/api/v1/gdpr/delete-account-now",
        params={"password": "wrong-password"},
        headers=headers,
    )

    assert response.status_code == 401


def test_delete_account_now_success(test_client, gdpr_test_user, db):
    headers = _login_headers(test_client, gdpr_test_user.email, "testpassword123")
    user_id = gdpr_test_user.id

    response = test_client.request(
        "DELETE",
        "/api/v1/gdpr/delete-account-now",
        params={"password": "testpassword123"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True

    db.expire_all()
    assert db.get(User, user_id) is None


def test_delete_account_now_returns_500_when_fail_closed_audit_log_fails(
    test_client, gdpr_test_user, db
):
    """Der Fail-Closed-`RuntimeError` aus `delete_user_and_gdpr_data`
    (Audit-Log-Schreibfehler) muss über den echten HTTP-Endpoint als 500
    ankommen — UND der User darf dabei nicht gelöscht werden.

    Patcht bewusst ``services.gdpr_deletion_service.AuditService.log_action``
    (löst den echten Fail-Closed-Pfad aus), NICHT
    ``api.gdpr.delete_user_and_gdpr_data``. Historischer Grund (bis TF-660):
    `main.py` lud `api/gdpr.py` zusätzlich als zweites, nie in `sys.modules`
    registriertes Modulobjekt (`core_api_gdpr`) und registrierte dessen
    Router — welches Modulobjekt die Route bediente, hing von der
    Testreihenfolge ab, und ein danebengreifender Patch hätte hier lautlos
    eine ECHTE Kontolöschung ausgelöst. Seit TF-660 lädt `main.py` die
    `api/`-Module unter ihrem kanonischen Namen, es gibt also nur noch eine
    Instanz. Der Patch bleibt trotzdem auf dem Service: er trifft den echten
    Fail-Closed-Pfad statt ihn wegzumocken, und der Preis eines Fehlgriffs
    wäre hier besonders hoch."""
    headers = _login_headers(test_client, gdpr_test_user.email, "testpassword123")
    user_id = gdpr_test_user.id

    with patch(
        "services.gdpr_deletion_service.AuditService.log_action",
        return_value=None,
    ):
        response = test_client.request(
            "DELETE",
            "/api/v1/gdpr/delete-account-now",
            params={"password": "testpassword123"},
            headers=headers,
        )

    assert response.status_code == 500

    db.expire_all()
    assert db.get(User, user_id) is not None

    db.expire_all()
    assert db.get(User, user_id) is not None
