/**
 * ExamCraft AI - Core Package Entry Point
 *
 * This file exports all public APIs from the Core package.
 * Premium and Enterprise packages import from this entry point.
 */

// ============================================================================
// Types
// ============================================================================

// Re-export all types from types/index.ts
export * from './types';

// ============================================================================
// Services
// ============================================================================

export { default as AuthService } from './services/AuthService';
export { default as DocumentService } from './services/DocumentService';
export { default as AdminService } from './services/AdminService';
export { default as ExamService } from './services/ExamService';
export { default as ReviewService } from './services/ReviewService';
export { default as RBACService } from './services/RBACService';

// ============================================================================
// Components
// ============================================================================

// Layout Components
export { default as AppLayout } from './components/layout/AppLayout';
export { default as DashboardLayout } from './components/layout/DashboardLayout';
export { default as NavigationBar } from './components/layout/NavigationBar';
export { default as Sidebar } from './components/layout/Sidebar';
export { default as PackageTierBadge } from './components/layout/PackageTierBadge';

// Auth Components
export { default as LoginForm } from './components/auth/LoginForm';
export { default as RegisterForm } from './components/auth/RegisterForm';
export { default as AuthPage } from './components/auth/AuthPage';
export { default as OAuthCallback } from './components/auth/OAuthCallback';
export { default as PasswordResetRequest } from './components/auth/PasswordResetRequest';
export { default as PasswordResetConfirm } from './components/auth/PasswordResetConfirm';

// Form Components
export { default as Button } from './components/form/Button';
export { default as Input } from './components/form/Input';
export { default as Select } from './components/form/Select';

// Card Components
export { default as QuickActionCard } from './components/cards/QuickActionCard';
export { default as StatsCard } from './components/cards/StatsCard';

// Document Components
export { default as DocumentUpload } from './components/DocumentUpload';
export { default as DocumentLibrary } from './components/DocumentLibrary';

// Question Components
export { default as QuestionEditor } from './components/QuestionEditor';
export { default as ReviewQueue } from './components/ReviewQueue';

// Admin Components
export { default as UserManagementPage } from './components/admin/UserManagementPage';
export { default as InstitutionManagementPage } from './components/admin/InstitutionManagementPage';
export { default as RoleManagementPage } from './components/admin/RoleManagementPage';
export { default as PromptLibrary } from './components/admin/PromptLibrary';
export { default as PromptManagement } from './components/admin/PromptManagement';
export { default as FeaturePermissionsMatrix } from './components/admin/FeaturePermissionsMatrix';
export { default as SubscriptionTierOverview } from './components/admin/SubscriptionTierOverview';

// ============================================================================
// Contexts
// ============================================================================

export { AuthProvider, useAuth } from './contexts/AuthContext';

// ============================================================================
// Utils
// ============================================================================

export { default as componentLoader } from './utils/componentLoader';
export { default as deploymentMode } from './utils/deploymentMode';

// ============================================================================
// Config
// ============================================================================

export { default as config } from './config';
