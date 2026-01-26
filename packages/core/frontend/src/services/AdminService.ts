/**
 * Admin Service
 * API calls for admin user management
 */

import { Role, Institution, UserStatus } from '../types/auth';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface UserListItem {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  institution_id: number;
  institution_name: string;
  roles: string[];
  status: string;
  is_superuser: boolean;
  last_login_at?: string;
  created_at: string;
}

export interface UserListResponse {
  users: UserListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserDetailResponse {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  institution_id: number;
  institution_name: string;
  roles: Role[];
  status: string;
  is_superuser: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface UpdateUserRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
}

export interface UpdateUserStatusRequest {
  status: UserStatus;
}

export interface AssignRoleRequest {
  role_id: number;
}

export interface ListUsersParams {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  status?: string;
  institution_id?: number;
}

class AdminService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('examcraft_access_token');
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  /**
   * List all users with pagination and filters
   */
  async listUsers(params: ListUsersParams = {}): Promise<UserListResponse> {
    const queryParams = new URLSearchParams();

    if (params.page) queryParams.append('page', params.page.toString());
    if (params.page_size) queryParams.append('page_size', params.page_size.toString());
    if (params.search) queryParams.append('search', params.search);
    if (params.role) queryParams.append('role', params.role);
    if (params.status) queryParams.append('status', params.status);
    if (params.institution_id) queryParams.append('institution_id', params.institution_id.toString());

    const response = await fetch(
      `${API_BASE_URL}/api/admin/users?${queryParams.toString()}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch users');
    }

    return response.json();
  }

  /**
   * Get user details by ID
   */
  async getUser(userId: number): Promise<UserDetailResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/users/${userId}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch user');
    }

    return response.json();
  }

  /**
   * Update user details
   */
  async updateUser(userId: number, data: UpdateUserRequest): Promise<UserDetailResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/users/${userId}`,
      {
        method: 'PATCH',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update user');
    }

    return response.json();
  }

  /**
   * Update user status (activate/deactivate)
   */
  async updateUserStatus(userId: number, status: UserStatus): Promise<UserDetailResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/users/${userId}/status`,
      {
        method: 'PATCH',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ status }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update user status');
    }

    return response.json();
  }

  /**
   * Assign role to user
   */
  async assignRole(userId: number, roleId: number): Promise<UserDetailResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/users/${userId}/roles`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ role_id: roleId }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to assign role');
    }

    return response.json();
  }

  /**
   * Remove role from user
   */
  async removeRole(userId: number, roleId: number): Promise<UserDetailResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/users/${userId}/roles/${roleId}`,
      {
        method: 'DELETE',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to remove role');
    }

    return response.json();
  }

  /**
   * List all available roles
   */
  async listRoles(): Promise<Role[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/roles`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch roles');
    }

    return response.json();
  }

  /**
   * List all institutions
   */
  async listInstitutions(): Promise<Institution[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/institutions`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch institutions');
    }

    return response.json();
  }

  /**
   * Update institution
   */
  async updateInstitution(
    institutionId: number,
    data: {
      name?: string;
      domain?: string;
      subscription_tier?: string;
      is_active?: boolean;
    }
  ): Promise<Institution> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/institutions/${institutionId}`,
      {
        method: 'PATCH',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update institution');
    }

    return response.json();
  }

  /**
   * Create institution
   */
  async createInstitution(data: {
    name: string;
    domain: string;
    subscription_tier?: string;
  }): Promise<Institution> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/institutions`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create institution');
    }

    return response.json();
  }
}

const adminService = new AdminService();
export default adminService;
