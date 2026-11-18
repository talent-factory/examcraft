/**
 * Admin Service
 * API calls for admin user management
 */

import { Role, Institution, UserStatus } from '../types/auth';
import { OrgUnitMember } from '../types/orgUnit';
import { appErrorFromResponse } from '../errors';

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
  can_edit: boolean;
}

/** Response of `POST /api/admin/users/{id}/impersonate` (TF-741/TF-743). */
export interface ImpersonateResponse {
  expires_in: number;
  /** Server-side end of the impersonation (ISO 8601); preferred over `expires_in`. */
  expires_at?: string;
  impersonation_session_id: number;
  target_user_id: number;
  target_user_email: string;
}

export interface UserDetailResponse {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  institution_id: number;
  institution_name: string;
  roles: Role[];
  org_units: OrgUnitMember[];
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

export interface TransferUserRequest {
  target_institution_id: number;
  transfer_documents?: boolean;
  transfer_exams?: boolean;
  transfer_questions?: boolean;
  transfer_tags?: boolean;
}

export interface TransferPreviewCounts {
  documents: number;
  exams: number;
  questions: number;
  tags: number;
}

export interface TransferExcludedCounts {
  students: number;
  classes: number;
  submissions: number;
}

export interface TransferPreviewResponse {
  source_institution_id: number;
  source_institution_name: string;
  target_institution_id: number;
  target_institution_name: string;
  transferable: TransferPreviewCounts;
  excluded: TransferExcludedCounts;
  /** Org-unit memberships that will be cleared by the transfer (TF-602). */
  org_unit_memberships: number;
}

export interface TransferUserResponse {
  user: UserDetailResponse;
  transferred: TransferPreviewCounts;
  /** Org-unit memberships actually cleared by the transfer (TF-602). */
  org_unit_memberships_cleared: number;
}

class AdminService {
  // The session cookie travels with every request (credentials: 'include' via
  // the fetch interceptor, EXAMCRAFT-126); only the content type is set here.
  private getAuthHeaders(): HeadersInit {
    return { 'Content-Type': 'application/json' };
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
      throw await appErrorFromResponse(response, 'admin_users_load_failed');
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
      throw await appErrorFromResponse(response, 'admin_user_load_failed');
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
      throw await appErrorFromResponse(response, 'admin_user_update_failed');
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
      throw await appErrorFromResponse(response, 'admin_user_status_update_failed');
    }

    return response.json();
  }

  /**
   * Start impersonating a user (TF-741/TF-743). Requires `users:impersonate`;
   * scope (SuperAdmin: anyone; institution admin: non-admin users of the
   * same institution) is enforced server-side.
   */
  async impersonateUser(
    userId: number,
    reason: string
  ): Promise<ImpersonateResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/users/${userId}/impersonate`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ reason }),
      }
    );

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'impersonation_start_failed');
    }

    return response.json();
  }

  /**
   * Ends the active impersonation session (TF-741). The backend identifies the
   * session through the impersonation cookie of the request.
   */
  async endImpersonation(): Promise<void> {
    const headers = this.getAuthHeaders();

    const response = await fetch(
      `${API_BASE_URL}/api/admin/impersonate/end`,
      {
        method: 'POST',
        headers,
      }
    );

    if (!response.ok && response.status !== 204) {
      throw await appErrorFromResponse(response, 'impersonation_end_failed');
    }
  }

  /**
   * Preview which artifacts would transfer if user is moved to target institution.
   * SuperAdmin only.
   */
  async previewTransfer(
    userId: number,
    targetInstitutionId: number,
  ): Promise<TransferPreviewResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/users/${userId}/transfer-preview` +
        `?target_institution_id=${targetInstitutionId}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      },
    );
    if (!response.ok) {
      throw await appErrorFromResponse(response, 'admin_transfer_preview_failed');
    }
    return response.json();
  }

  /**
   * Execute institution transfer for a user. SuperAdmin only.
   */
  async transferUser(
    userId: number,
    body: TransferUserRequest,
  ): Promise<TransferUserResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/users/${userId}/transfer`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) {
      throw await appErrorFromResponse(response, 'admin_transfer_failed');
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
      throw await appErrorFromResponse(response, 'admin_role_assign_failed');
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
      throw await appErrorFromResponse(response, 'admin_role_remove_failed');
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
      throw await appErrorFromResponse(response, 'admin_roles_load_failed');
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
      throw await appErrorFromResponse(response, 'admin_institutions_load_failed');
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
      default_grading_scheme_id?: number | null;
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
      throw await appErrorFromResponse(response, 'admin_institution_update_failed');
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
    default_grading_scheme_id?: number | null;
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
      throw await appErrorFromResponse(response, 'admin_institution_create_failed');
    }

    return response.json();
  }
}

const adminService = new AdminService();
export default adminService;
