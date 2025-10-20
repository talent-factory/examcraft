/**
 * RBAC Type Definitions
 * Types for Role-Based Access Control, Features, Permissions and Quotas
 */

// ============================================
// FEATURE TYPES
// ============================================

export interface Feature {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  category: string | null;
  is_active: boolean;
}

export type FeatureCategory = 'generation' | 'management' | 'administration' | 'integration' | 'other';

// ============================================
// ROLE TYPES
// ============================================

export interface Role {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  is_system_role: boolean;
  is_active: boolean;
  features: Feature[];
}

export interface CreateRoleRequest {
  name: string;
  display_name: string;
  description?: string;
  feature_ids: string[];
}

export interface UpdateRoleFeaturesRequest {
  feature_ids: string[];
}

// ============================================
// SUBSCRIPTION TIER TYPES
// ============================================

export interface SubscriptionTier {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  price_monthly: number;
  price_yearly: number;
  is_active: boolean;
  sort_order: number;
}

export interface TierQuota {
  tier_id: string;
  resource_type: string;
  quota_limit: number; // -1 = unlimited
}

export type ResourceType = 'documents' | 'questions_per_month' | 'users' | 'storage_mb';

// ============================================
// PERMISSION & QUOTA CHECK TYPES
// ============================================

export interface PermissionCheckResponse {
  has_access: boolean;
  feature: string;
}

export interface QuotaCheckResponse {
  allowed: boolean;
  current_usage?: number;
  quota_limit?: number;
  remaining?: number;
  requested?: number;
  reason?: string;
}

// ============================================
// UI HELPER TYPES
// ============================================

export interface FeatureGroup {
  category: FeatureCategory;
  features: Feature[];
}

export interface RoleWithPermissions extends Role {
  featureIds: string[];
}

export interface TierWithQuotas extends SubscriptionTier {
  quotas: TierQuota[];
}

// ============================================
// CONSTANTS
// ============================================

export const FEATURE_CATEGORIES: Record<FeatureCategory, string> = {
  generation: 'Generierung',
  management: 'Verwaltung',
  administration: 'Administration',
  integration: 'Integration',
  other: 'Sonstige'
};

export const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  documents: 'Dokumente',
  questions_per_month: 'Fragen pro Monat',
  users: 'Benutzer',
  storage_mb: 'Speicher (MB)'
};

export const TIER_COLORS: Record<string, string> = {
  tier_free: '#9E9E9E',
  tier_starter: '#2196F3',
  tier_professional: '#4CAF50',
  tier_enterprise: '#FF9800'
};

