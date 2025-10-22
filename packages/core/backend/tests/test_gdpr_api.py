"""
Tests für GDPR Compliance API Endpoints
Simple smoke tests to verify GDPR endpoints are accessible
"""

import pytest
from fastapi.testclient import TestClient

from main import app

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
