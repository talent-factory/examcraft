"""
RBAC Service für ExamCraft AI
Implementiert Permission Checks, Quota Management, Role Management und Audit Logging
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
import logging

from models.rbac import (
    Feature,
    RBACRole,
    RoleFeature,
    TierQuota,
    TierFeature,
    ResourceUsage,
    PermissionAuditLog,
)
from models.auth import User

logger = logging.getLogger(__name__)


class RBACService:
    """
    Service für Role-Based Access Control, Feature-Permissions und Ressourcen-Quotas.
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================
    # PERMISSION CHECKS
    # ============================================

    def user_has_feature_access(
        self, user_id: int, feature_name: str, log_access: bool = True
    ) -> bool:
        """
        Prüft ob ein User Zugriff auf ein Feature hat.
        Berücksichtigt sowohl Rolle als auch Subscription Tier.

        Args:
            user_id: User ID
            feature_name: Feature-Name (z.B. 'question_generation_ai')
            log_access: Ob Zugriff geloggt werden soll

        Returns:
            True wenn User Zugriff hat, sonst False
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Feature holen
        feature = (
            self.db.query(Feature)
            .filter(Feature.name == feature_name, Feature.is_active)
            .first()
        )

        if not feature:
            logger.warning(f"Feature '{feature_name}' not found or inactive")
            return False

        # 1. Check: Hat die Rolle des Users Zugriff auf das Feature?
        # Prüfe gegen bestehende 'roles' Tabelle (user.roles Relationship)
        role_has_feature = False
        for role in user.roles:
            # Mappe alte Rolle auf neue RBAC-Rolle
            rbac_role_id = f"role_{role.name}"
            role_feature = (
                self.db.query(RoleFeature)
                .filter(
                    and_(
                        RoleFeature.role_id == rbac_role_id,
                        RoleFeature.feature_id == feature.id,
                    )
                )
                .first()
            )
            if role_feature:
                role_has_feature = True
                break

        if not role_has_feature:
            if log_access:
                self._log_access_denied(
                    user_id, "feature", feature_name, "role_permission_denied"
                )
            return False

        # 2. Check: Hat das Subscription Tier Zugriff auf das Feature?
        # Prüfe gegen Institution (die bereits subscription_tier hat)
        if user.institution_id:
            institution = user.institution
            if institution and institution.subscription_tier:
                # Mappe Institution.subscription_tier auf SubscriptionTier
                tier_id = f"tier_{institution.subscription_tier}"
                tier_has_feature = (
                    self.db.query(TierFeature)
                    .filter(
                        and_(
                            TierFeature.tier_id == tier_id,
                            TierFeature.feature_id == feature.id,
                        )
                    )
                    .first()
                    is not None
                )

                if not tier_has_feature:
                    if log_access:
                        self._log_access_denied(
                            user_id, "feature", feature_name, "tier_permission_denied"
                        )
                    return False

        # 3. Alles OK - Zugriff erlauben
        if log_access:
            self._log_access_granted(user_id, "feature", feature_name)

        return True

    def check_resource_quota(
        self, institution_id: int, resource_type: str, requested_amount: int = 1
    ) -> Dict[str, Any]:
        """
        Prüft ob eine Institution noch Ressourcen-Quota verfügbar hat.

        Args:
            institution_id: Institution ID (entspricht Organization)
            resource_type: z.B. 'documents', 'questions_per_month'
            requested_amount: Anzahl der angefragten Ressourcen

        Returns:
            Dict mit 'allowed': bool, 'current_usage': int, 'quota_limit': int, 'remaining': int
        """
        from models.auth import Institution

        institution = (
            self.db.query(Institution).filter(Institution.id == institution_id).first()
        )
        if not institution:
            return {"allowed": False, "reason": "institution_not_found"}

        # Quota Limit für diesen Tier holen
        tier_id = f"tier_{institution.subscription_tier}"
        tier_quota = (
            self.db.query(TierQuota)
            .filter(
                and_(
                    TierQuota.tier_id == tier_id,
                    TierQuota.resource_type == resource_type,
                )
            )
            .first()
        )

        if not tier_quota:
            return {
                "allowed": True,
                "reason": "no_quota_defined",
            }  # Kein Limit = erlaubt

        quota_limit = tier_quota.quota_limit
        if quota_limit == -1:
            return {
                "allowed": True,
                "current_usage": 0,
                "quota_limit": -1,
                "remaining": -1,
            }  # Unlimited

        # Aktuelle Nutzung ermitteln
        current_period_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        (current_period_start + timedelta(days=32)).replace(day=1) - timedelta(
            seconds=1
        )

        usage = (
            self.db.query(ResourceUsage)
            .filter(
                and_(
                    ResourceUsage.institution_id == institution_id,
                    ResourceUsage.resource_type == resource_type,
                    ResourceUsage.period_start == current_period_start,
                )
            )
            .first()
        )

        current_usage = usage.usage_count if usage else 0
        remaining = quota_limit - current_usage
        allowed = remaining >= requested_amount

        return {
            "allowed": allowed,
            "current_usage": current_usage,
            "quota_limit": quota_limit,
            "remaining": remaining,
            "requested": requested_amount,
        }

    def increment_resource_usage(
        self, institution_id: int, resource_type: str, amount: int = 1
    ) -> ResourceUsage:
        """
        Erhöht die Ressourcen-Nutzung für eine Institution.
        """
        current_period_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        current_period_end = (current_period_start + timedelta(days=32)).replace(
            day=1
        ) - timedelta(seconds=1)

        usage = (
            self.db.query(ResourceUsage)
            .filter(
                and_(
                    ResourceUsage.institution_id == institution_id,
                    ResourceUsage.resource_type == resource_type,
                    ResourceUsage.period_start == current_period_start,
                )
            )
            .first()
        )

        if not usage:
            usage = ResourceUsage(
                institution_id=institution_id,
                resource_type=resource_type,
                usage_count=0,
                period_start=current_period_start,
                period_end=current_period_end,
            )
            self.db.add(usage)

        usage.usage_count += amount
        usage.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(usage)

        return usage

    # ============================================
    # ROLE MANAGEMENT
    # ============================================

    def create_custom_role(
        self,
        name: str,
        display_name: str,
        description: Optional[str],
        feature_ids: List[str],
        created_by: int,
    ) -> RBACRole:
        """
        Erstellt eine neue Custom-Rolle mit zugeordneten Features.
        """
        # Validierung: Name darf nur lowercase, alphanumeric, underscore
        if not name.replace("_", "").isalnum() or name != name.lower():
            raise ValueError(
                "Role name must be lowercase alphanumeric with underscores"
            )

        # Prüfen ob Name bereits existiert
        existing = self.db.query(RBACRole).filter(RBACRole.name == name).first()
        if existing:
            raise ValueError(f"Role with name '{name}' already exists")

        role = RBACRole(
            id=f"role_{name}",
            name=name,
            display_name=display_name,
            description=description,
            is_system_role=False,
            is_active=True,
            created_by=str(created_by),
        )
        self.db.add(role)
        self.db.flush()

        # Features zuordnen
        for feature_id in feature_ids:
            role_feature = RoleFeature(role_id=role.id, feature_id=feature_id)
            self.db.add(role_feature)

        self.db.commit()
        self.db.refresh(role)
        return role

    def update_role_features(self, role_id: str, feature_ids: List[str]) -> RBACRole:
        """
        Aktualisiert die Features einer Rolle.
        """
        role = self.db.query(RBACRole).filter(RBACRole.id == role_id).first()
        if not role:
            raise ValueError(f"Role '{role_id}' not found")

        if role.is_system_role:
            raise ValueError("Cannot modify features of system roles")

        # Lösche bestehende Mappings
        self.db.query(RoleFeature).filter(RoleFeature.role_id == role_id).delete()

        # Neue Mappings erstellen
        for feature_id in feature_ids:
            role_feature = RoleFeature(role_id=role_id, feature_id=feature_id)
            self.db.add(role_feature)

        self.db.commit()
        self.db.refresh(role)
        return role

    def list_roles(
        self, include_system_roles: bool = True, include_inactive: bool = False
    ) -> List[RBACRole]:
        """
        Listet alle Rollen auf.
        """
        query = self.db.query(RBACRole)

        if not include_system_roles:
            query = query.filter(not RBACRole.is_system_role)

        if not include_inactive:
            query = query.filter(RBACRole.is_active)

        return query.all()

    def get_role_features(self, role_id: str) -> List[Feature]:
        """
        Gibt alle Features einer Rolle zurück.
        """
        return (
            self.db.query(Feature)
            .join(RoleFeature)
            .filter(and_(RoleFeature.role_id == role_id, Feature.is_active))
            .all()
        )

    # ============================================
    # AUDIT LOGGING
    # ============================================

    def _log_access_granted(self, user_id: int, resource_type: str, resource_id: str):
        log = PermissionAuditLog(
            user_id=str(user_id),
            action="access_granted",
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.now(),
        )
        self.db.add(log)
        self.db.commit()

    def _log_access_denied(
        self, user_id: int, resource_type: str, resource_id: str, reason: str
    ):
        log = PermissionAuditLog(
            user_id=str(user_id),
            action="access_denied",
            resource_type=resource_type,
            resource_id=resource_id,
            details={"reason": reason},
            timestamp=datetime.now(),
        )
        self.db.add(log)
        self.db.commit()
