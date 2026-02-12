/**
 * Authentication & User Management Types
 * TypeScript types for User, Role, Institution, and Auth State
 */

// ============================================================================
// Enums
// ============================================================================

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING = 'pending'
}

export enum UserRole {
  ADMIN = 'admin',
  DOZENT = 'dozent',
  ASSISTANT = 'assistant',
  VIEWER = 'viewer'
}

export enum SubscriptionTier {
  FREE = 'free',
  STARTER = 'starter',
  PROFESSIONAL = 'professional',
  ENTERPRISE = 'enterprise'
}

export enum OAuthProvider {
  GOOGLE = 'google',
  MICROSOFT = 'microsoft'
}

// ============================================================================
// Core Models
// ============================================================================

export interface Institution {
  id: number;
  name: string;
  slug: string;
  domain: string | null;
  subscription_tier: SubscriptionTier;
  max_users: number;
  max_documents: number;
  max_questions_per_month: number;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Role {
  id: number;
  name: UserRole;
  display_name: string;
  description: string;
  permissions: string[];
  is_system_role: boolean;
  created_at: string;
}

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  institution_id: number;
  institution?: Institution;
  roles: Role[];
  status: UserStatus;
  is_superuser: boolean;
  is_email_verified: boolean;  // Email verification status
  oauth_provider?: string;  // OAuth provider (google, microsoft, etc.)
  avatar_url?: string;  // Profile picture URL (from OAuth or uploaded)
  last_login?: string;
  created_at: string;
  updated_at?: string;
}

export interface OAuthAccount {
  id: number;
  user_id: number;
  provider: OAuthProvider;
  provider_user_id: string;
  email: string;
  created_at: string;
}

export interface UserSession {
  id: number;
  user_id: number;
  token: string;
  ip_address?: string;
  user_agent?: string;
  is_active: boolean;
  expires_at: string;
  created_at: string;
  revoked_at?: string;
}

export interface AuditLog {
  id: number;
  user_id?: number;
  action: string;
  resource_type?: string;
  resource_id?: string;
  ip_address?: string;
  user_agent?: string;
  additional_data?: Record<string, any>;
  status: 'success' | 'failure' | 'error';
  error_message?: string;
  created_at: string;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  institution_slug?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface SetPasswordRequest {
  password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirm {
  token: string;
  new_password: string;
}

export interface UpdateProfileRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
}

export interface UserResponse {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  institution_id: number;
  institution?: Institution;
  roles: Role[];
  status: UserStatus;
  is_superuser: boolean;
  is_email_verified: boolean;  // Email verification status
  oauth_provider?: string;  // OAuth provider (google, microsoft, etc.)
  avatar_url?: string;  // Profile picture URL (from OAuth or uploaded)
  last_login?: string;
  created_at: string;
}

// ============================================================================
// Auth State Types
// ============================================================================

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<void>;
  updateProfile: (data: UpdateProfileRequest) => Promise<void>;
  setPassword: (password: string) => Promise<void>;
  changePassword: (data: ChangePasswordRequest) => Promise<void>;
  clearError: () => void;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: UserRole) => boolean;
}

// ============================================================================
// OAuth Types
// ============================================================================

export interface OAuthLoginResponse {
  authorization_url: string;
}

export interface OAuthCallbackParams {
  code: string;
  state: string;
}

// ============================================================================
// Admin Types
// ============================================================================

export interface UserListItem {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  institution_id: number;
  institution_name: string;
  roles: string[];
  status: UserStatus;
  last_login?: string;
  created_at: string;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  institution_id: number;
  role_ids: number[];
}

export interface UpdateUserRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  status?: UserStatus;
  role_ids?: number[];
}

export interface AssignRoleRequest {
  user_id: number;
  role_id: number;
}

export interface RemoveRoleRequest {
  user_id: number;
  role_id: number;
}

// ============================================================================
// Subscription & Usage Types
// ============================================================================

export interface SubscriptionLimits {
  max_users: number;
  max_documents: number;
  max_questions_per_month: number;
}

export interface UsageStats {
  current_users: number;
  current_documents: number;
  current_questions_this_month: number;
  user_percentage: number;
  document_percentage: number;
  question_percentage: number;
}

export interface InstitutionUsage {
  institution: Institution;
  limits: SubscriptionLimits;
  usage: UsageStats;
}

// ============================================================================
// Utility Types
// ============================================================================

export type Permission = string;

export interface PermissionCheck {
  permission: Permission;
  granted: boolean;
}

export interface RoleCheck {
  role: UserRole;
  granted: boolean;
}
