"""
Tests for Security Features (PR #41)
JWT key validation of ``AuthService``.

Account lockout on /login, password-strength validation on register /
change-password and OAuth CSRF / code exchange were removed with the
endpoints themselves (EXAMCRAFT-125: login runs through Zitadel).
"""

from unittest.mock import patch

import pytest


# ============================================================================
# TestJWTKeyValidation
# ============================================================================


class TestJWTKeyValidation:
    """Test that AuthService raises RuntimeError without JWT key in production."""

    def test_missing_jwt_key_in_production_raises_error(self):
        """Should raise RuntimeError when JWT_SECRET_KEY is empty in production."""
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET_KEY": "",
                "ENVIRONMENT": "production",
                "DEPLOYMENT_MODE": "core",
            },
            clear=False,
        ):
            with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
                # Re-execute the module-level code that checks the key
                import importlib
                import services.auth_service

                importlib.reload(services.auth_service)

    def test_missing_jwt_key_in_full_mode_raises_error(self):
        """Should raise RuntimeError when JWT_SECRET_KEY is empty in full deployment mode."""
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET_KEY": "",
                "ENVIRONMENT": "development",
                "DEPLOYMENT_MODE": "full",
            },
            clear=False,
        ):
            with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
                import importlib
                import services.auth_service

                importlib.reload(services.auth_service)

    def test_missing_jwt_key_in_development_uses_default(self):
        """Should NOT raise in development mode, uses insecure default instead."""
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET_KEY": "",
                "ENVIRONMENT": "development",
                "DEPLOYMENT_MODE": "core",
            },
            clear=False,
        ):
            import importlib
            import services.auth_service

            # Should not raise, just warn
            importlib.reload(services.auth_service)
            assert services.auth_service.SECRET_KEY == (
                "insecure-dev-default-do-not-use-in-production"
            )

    def test_jwt_key_set_uses_provided_value(self):
        """Should use the provided JWT_SECRET_KEY when set."""
        with patch.dict(
            "os.environ",
            {
                "JWT_SECRET_KEY": "my-secure-secret-key-for-testing"  # pragma: allowlist secret
            },
            clear=False,
        ):
            import importlib
            import services.auth_service

            importlib.reload(services.auth_service)
            assert (
                services.auth_service.SECRET_KEY
                == "my-secure-secret-key-for-testing"  # pragma: allowlist secret
            )
