/**
 * Central Type Exports
 * Re-export all types for easier imports
 */

// Auth Types
export * from './auth';

// Document Types
export * from './document';

// Exam Types
export * from './exam';

// Review Types
export * from './review';

// Prompt Types
export * from './prompt';

// RBAC Types - Selective export to avoid conflicts with auth.ts
export type {
  Feature,
  FeatureCategory,
  TierQuota,
  ResourceType,
  CreateRoleRequest,
  UpdateRoleFeaturesRequest,
  PermissionCheckResponse,
  QuotaCheckResponse,
  FeatureGroup,
  RoleWithPermissions,
  TierWithQuotas
} from './rbac';

// Export RBAC types with aliases to avoid conflicts
export type { Role as RBACRole, SubscriptionTier as RBACSubscriptionTier } from './rbac';

// Export RBAC constants
export { FEATURE_CATEGORIES, RESOURCE_TYPE_LABELS, TIER_COLORS } from './rbac';
