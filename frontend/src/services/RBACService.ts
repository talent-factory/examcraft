/**
 * RBAC Service
 * API calls for Role-Based Access Control, Features, Permissions and Quotas
 */

import {
  Feature,
  Role,
  SubscriptionTier,
  TierQuota,
  PermissionCheckResponse,
  QuotaCheckResponse,
  CreateRoleRequest,
  UpdateRoleFeaturesRequest
} from '../types/rbac';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class RBACService {
  /**
   * Get authentication token from localStorage
   */
  private getAuthToken(): string | null {
    return localStorage.getItem('examcraft_access_token');
  }

  /**
   * Get authorization headers
   */
  private getAuthHeaders(): HeadersInit {
    const token = this.getAuthToken();
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    };
  }

  // ============================================
  // FEATURE ENDPOINTS
  // ============================================

  /**
   * List all features
   */
  async listFeatures(category?: string, activeOnly: boolean = true): Promise<Feature[]> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    params.append('active_only', activeOnly.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/features?${params.toString()}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders()
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch features');
    }

    return response.json();
  }

  /**
   * Get feature by ID
   */
  async getFeature(featureId: string): Promise<Feature> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/features/${featureId}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders()
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch feature');
    }

    return response.json();
  }

  // ============================================
  // ROLE ENDPOINTS
  // ============================================

  /**
   * List all roles
   */
  async listRoles(
    includeSystemRoles: boolean = true,
    includeInactive: boolean = false
  ): Promise<Role[]> {
    const params = new URLSearchParams();
    params.append('include_system_roles', includeSystemRoles.toString());
    params.append('include_inactive', includeInactive.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/roles?${params.toString()}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders()
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch roles');
    }

    return response.json();
  }

  /**
   * Get role by ID
   */
  async getRole(roleId: string): Promise<Role> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/roles/${roleId}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders()
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch role');
    }

    return response.json();
  }

  /**
   * Create a new custom role
   */
  async createRole(data: CreateRoleRequest): Promise<Role> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/roles`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(data)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create role');
    }

    return response.json();
  }

  /**
   * Update role features
   */
  async updateRoleFeatures(
    roleId: string,
    data: UpdateRoleFeaturesRequest
  ): Promise<Role> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/roles/${roleId}/features`,
      {
        method: 'PUT',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(data)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update role features');
    }

    return response.json();
  }

  // ============================================
  // SUBSCRIPTION TIER ENDPOINTS
  // ============================================

  /**
   * List all subscription tiers (public endpoint)
   */
  async listSubscriptionTiers(activeOnly: boolean = true): Promise<SubscriptionTier[]> {
    const params = new URLSearchParams();
    params.append('active_only', activeOnly.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/tiers?${params.toString()}`,
      {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch subscription tiers');
    }

    return response.json();
  }

  /**
   * Get quotas for a subscription tier (public endpoint)
   */
  async getTierQuotas(tierId: string): Promise<TierQuota[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/tiers/${tierId}/quotas`,
      {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch tier quotas');
    }

    return response.json();
  }

  // ============================================
  // PERMISSION & QUOTA CHECK ENDPOINTS
  // ============================================

  /**
   * Check if current user has permission for a feature
   */
  async checkPermission(featureName: string): Promise<PermissionCheckResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/check-permission/${featureName}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders()
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to check permission');
    }

    return response.json();
  }

  /**
   * Check resource quota for current user's institution
   */
  async checkQuota(
    resourceType: string,
    requestedAmount: number = 1
  ): Promise<QuotaCheckResponse> {
    const params = new URLSearchParams();
    params.append('requested_amount', requestedAmount.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/v1/rbac/check-quota/${resourceType}?${params.toString()}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders()
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to check quota');
    }

    return response.json();
  }

  // ============================================
  // HELPER METHODS
  // ============================================

  /**
   * Get features grouped by category
   */
  async getFeaturesByCategory(): Promise<Record<string, Feature[]>> {
    const features = await this.listFeatures();
    const grouped: Record<string, Feature[]> = {};

    features.forEach(feature => {
      const category = feature.category || 'other';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(feature);
    });

    return grouped;
  }

  /**
   * Check if user has access to multiple features
   */
  async checkMultiplePermissions(featureNames: string[]): Promise<Record<string, boolean>> {
    const results: Record<string, boolean> = {};

    await Promise.all(
      featureNames.map(async (featureName) => {
        try {
          const response = await this.checkPermission(featureName);
          results[featureName] = response.has_access;
        } catch (error) {
          results[featureName] = false;
        }
      })
    );

    return results;
  }
}

const rbacService = new RBACService();
export default rbacService;
