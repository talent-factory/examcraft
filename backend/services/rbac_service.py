"""
RBAC Service for ExamCraft AI
Implements permission checks, quota management, role management, and audit logging
"""

from typing import List, Dict, Any
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
    Service for role-based access control, feature permissions, and resource quotas.
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
        Check whether a user has access to a feature.
        Considers both role and subscription tier.

        Args:
            user_id: User ID
            feature_name: Feature name (e.g. 'question_generation_ai')
            log_access: Whether access should be logged

        Returns:
            True if the user has access, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Look up feature
        feature = (
            self.db.query(Feature)
            .filter(Feature.name == feature_name, Feature.is_active)
            .first()
        )

        if not feature:
            logger.warning(f"Feature '{feature_name}' not found or inactive")
            return False

        # 1. Check: does the user's role have access to the feature?
        # Check against the existing 'roles' table (user.roles relationship)
        role_has_feature = False
        for role in user.roles:
            # Map old role to new RBAC role
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

        # 2. Check: does the subscription tier have access to the feature?
        # Check against institution (which already has subscription_tier)
        if user.institution_id:
            institution = user.institution
            if institution and institution.subscription_tier:
                # Map Institution.subscription_tier to SubscriptionTier
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

        # 3. All OK - allow access
        if log_access:
            self._log_access_granted(user_id, "feature", feature_name)

        return True

    def check_resource_quota(
        self, institution_id: int, resource_type: str, requested_amount: int = 1
    ) -> Dict[str, Any]:
        """
        Check whether an institution still has resource quota available.

        Args:
            institution_id: Institution ID (corresponds to organization)
            resource_type: e.g. 'documents', 'questions_per_month'
            requested_amount: Number of requested resources

        Returns:
            Dict with 'allowed': bool, 'current_usage': int, 'quota_limit': int, 'remaining': int
        """
        from models.auth import Institution

        institution = (
            self.db.query(Institution).filter(Institution.id == institution_id).first()
        )
        if not institution:
            return {"allowed": False, "reason": "institution_not_found"}

        # Get the quota limit for this tier
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
            }  # No limit = allowed

        quota_limit = tier_quota.quota_limit
        if quota_limit == -1:
            return {
                "allowed": True,
                "current_usage": 0,
                "quota_limit": -1,
                "remaining": -1,
            }  # Unlimited

        # Determine current usage
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
        Increases resource usage for an institution.
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

    def list_roles(
        self, include_system_roles: bool = True, include_inactive: bool = False
    ) -> List[RBACRole]:
        """
        Lists all roles.
        """
        query = self.db.query(RBACRole)

        if not include_system_roles:
            query = query.filter(not RBACRole.is_system_role)

        if not include_inactive:
            query = query.filter(RBACRole.is_active)

        return query.all()

    def get_role_features(self, role_id: str) -> List[Feature]:
        """
        Returns all features of a role.
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
