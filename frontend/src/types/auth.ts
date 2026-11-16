/**
 * Authentication & User Management Types
 * TypeScript types for User, Role, Institution, and Auth State
 */

// ============================================================================
// Language Type
// ============================================================================

export type SupportedLanguage = 'de' | 'en' | 'fr' | 'it';

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
  default_grading_scheme_id: number | null;
  created_at: string;
  updated_at?: string;
}

export interface Role {
  id: number;
  name: string;
  display_name: string;
  // Nullable: matches the backend's Role.description (Column(Text,
  // nullable=True)) and api.admin.RoleResponse.description: Optional[str].
  // A role created via POST /api/admin/roles with no description, or a
  // system role seeded without one, legitimately has description: null —
  // treating it as always a `string` here let call sites assume they could
  // safely call string methods on it (TF-603 review follow-up).
  description: string | null;
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
  previous_login_at?: string | null;  // Login before the current one (TF-1060)
  created_at: string;
  updated_at?: string;
  preferred_language?: SupportedLanguage;
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

export interface UpdateProfileRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  preferred_language?: SupportedLanguage;
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
  previous_login_at?: string | null;  // Login before the current one (TF-1060)
  created_at: string;
  preferred_language?: SupportedLanguage;
}

// ============================================================================
// Auth State Types
// ============================================================================

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  /** True while `user` reflects an impersonated target, not the admin who started the session (TF-743). */
  isImpersonating: boolean;
  /** ISO timestamp of the impersonation token's hard TF-741 30-min cap, or null when not impersonating. */
  impersonationExpiresAt: string | null;
}

export interface AuthContextType extends AuthState {
  /**
   * Leitet das ganze Fenster auf den Login-Flow des Backends
   * (`/api/v1/auth/login`, OIDC gegen tessera/Zitadel). `reauth` erzwingt eine
   * frische Anmeldung beim IdP (Step-up, z. B. vor einer Impersonation).
   * `returnTo`: relative in-app path (e.g. `/admin`) to return to afterwards; the
   * backend only accepts allowlisted paths.
   */
  login: (options?: { reauth?: boolean; returnTo?: string }) => void;
  /** Resolves with `backendEndFailed` when an impersonation could not be ended (the user stays signed in as the target). */
  logout: () => Promise<{ backendEndFailed: boolean } | void>;
  updateProfile: (data: UpdateProfileRequest) => Promise<void>;
  clearError: () => void;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: UserRole) => boolean;
  /**
   * Übernimmt eine soeben gestartete Impersonation (`POST
   * /api/admin/users/{id}/impersonate` hat das Impersonation-Cookie gesetzt):
   * lädt das Profil des Ziel-Benutzers neu und merkt sich die Laufzeit.
   */
  startImpersonation: (payload: { expiresIn: number }) => Promise<void>;
  /**
   * Beendet die Impersonation (`POST /api/admin/impersonate/end`) und lädt das
   * Profil des Admins neu. Ist keine Impersonation aktiv, passiert nichts.
   * `backendEndFailed` meldet, ob der Server-Aufruf fehlschlug; lokal fällt die
   * Anzeige in jedem Fall auf den Admin zurück.
   */
  endImpersonation: () => Promise<{ backendEndFailed: boolean }>;
}

// ============================================================================
// Admin Types
// ============================================================================

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
