"""
RBAC Middleware für ExamCraft AI
Automatische Permission-Checks auf API-Routen basierend auf Features
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import logging

from services.rbac_service import RBACService
from database import SessionLocal

logger = logging.getLogger(__name__)


class RBACMiddleware(BaseHTTPMiddleware):
    """
    Middleware für automatische Permission-Checks auf API-Routen.
    Prüft ob User Zugriff auf Features hat und ob Ressourcen-Quotas eingehalten werden.
    """

    # Mapping von API-Routen zu benötigten Features
    ROUTE_FEATURE_MAP = {
        "/api/v1/questions/generate": "question_generation_ai",
        "/api/v1/documents/upload": "document_upload",
        "/api/v1/documents": "document_library",
        "/api/v1/rag/generate": "rag_generation",
        "/api/v1/rag/exams": "rag_generation",
        "/api/v1/chat": "document_chatbot",
        "/api/v1/review": "question_review",
        "/api/v1/prompts": "prompt_management",
        "/api/v1/admin/users": "user_management",
        "/api/v1/config": "system_configuration",
        "/api/v1/analytics": "analytics_dashboard",
    }

    # Öffentliche Routen (keine Permission-Checks)
    PUBLIC_ROUTES = [
        "/api/v1/auth/",
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Hauptfunktion der Middleware - wird für jeden Request aufgerufen
        """
        # Öffentliche Routen überspringen
        if self._is_public_route(request.url.path):
            return await call_next(request)

        # User aus Request State extrahieren (gesetzt durch auth_middleware)
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Feature für Route ermitteln
        feature_name = self._get_required_feature(request.url.path)
        if not feature_name:
            # Keine spezifische Feature-Requirement - Request durchlassen
            return await call_next(request)

        # Permission Check
        db = SessionLocal()
        try:
            rbac_service = RBACService(db)

            has_access = rbac_service.user_has_feature_access(
                user_id=user_id, feature_name=feature_name, log_access=True
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Missing permission for feature '{feature_name}'",
                )

            # Resource Quota Check für POST/PUT/DELETE Requests
            if request.method in ["POST", "PUT", "DELETE"]:
                institution_id = getattr(request.state, "institution_id", None)
                if institution_id:
                    resource_type = self._get_resource_type(
                        request.url.path, request.method
                    )
                    if resource_type:
                        quota_check = rbac_service.check_resource_quota(
                            institution_id=institution_id, resource_type=resource_type
                        )
                        if not quota_check["allowed"]:
                            raise HTTPException(
                                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail=f"Resource quota exceeded: {quota_check}",
                            )

                        # Quota erfolgreich geprüft - nach Request inkrementieren
                        request.state.increment_quota = {
                            "institution_id": institution_id,
                            "resource_type": resource_type,
                            "amount": 1,
                        }

            # Request durchführen
            response = await call_next(request)

            # Nach erfolgreichem Request: Quota inkrementieren
            if hasattr(request.state, "increment_quota") and response.status_code < 400:
                quota_info = request.state.increment_quota
                rbac_service.increment_resource_usage(
                    institution_id=quota_info["institution_id"],
                    resource_type=quota_info["resource_type"],
                    amount=quota_info["amount"],
                )

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"RBAC Middleware Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during permission check",
            )
        finally:
            db.close()

    def _is_public_route(self, path: str) -> bool:
        """
        Prüft ob Route öffentlich ist (keine Permission-Checks)
        """
        for public_route in self.PUBLIC_ROUTES:
            if path.startswith(public_route):
                return True
        return False

    def _get_required_feature(self, path: str) -> Optional[str]:
        """
        Ermittelt das benötigte Feature für einen API-Pfad.
        """
        for route_pattern, feature in self.ROUTE_FEATURE_MAP.items():
            if path.startswith(route_pattern):
                return feature
        return None

    def _get_resource_type(self, path: str, method: str) -> Optional[str]:
        """
        Ermittelt den Ressourcen-Typ für Quota-Tracking.
        """
        if "/documents" in path and method == "POST":
            return "documents"
        elif "/questions/generate" in path and method == "POST":
            return "questions_per_month"
        elif "/rag/generate" in path and method == "POST":
            return "questions_per_month"
        return None


# Dependency für manuelle Permission-Checks in Endpoints
def require_feature(feature_name: str):
    """
    Dependency für manuelle Feature-Permission-Checks in Endpoints.

    Usage:
        @router.get("/some-endpoint", dependencies=[Depends(require_feature("question_generation_ai"))])
        async def some_endpoint():
            ...
    """

    async def check_feature_permission(request: Request):
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        db = SessionLocal()
        try:
            rbac_service = RBACService(db)
            has_access = rbac_service.user_has_feature_access(
                user_id=user_id, feature_name=feature_name, log_access=True
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Missing permission for feature '{feature_name}'",
                )
        finally:
            db.close()

    return check_feature_permission


# Dependency für Quota-Checks
def check_quota(resource_type: str, amount: int = 1):
    """
    Dependency für manuelle Quota-Checks in Endpoints.

    Usage:
        @router.post("/upload", dependencies=[Depends(check_quota("documents", 1))])
        async def upload_document():
            ...
    """

    async def check_resource_quota(request: Request):
        institution_id = getattr(request.state, "institution_id", None)
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Institution ID required for quota check",
            )

        db = SessionLocal()
        try:
            rbac_service = RBACService(db)
            quota_check = rbac_service.check_resource_quota(
                institution_id=institution_id,
                resource_type=resource_type,
                requested_amount=amount,
            )

            if not quota_check["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Resource quota exceeded: {quota_check}",
                )

            # Quota erfolgreich geprüft - nach Request inkrementieren
            request.state.increment_quota = {
                "institution_id": institution_id,
                "resource_type": resource_type,
                "amount": amount,
            }
        finally:
            db.close()

    return check_resource_quota
