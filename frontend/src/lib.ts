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
export { default as AdminService } from './services/AdminService';
export { default as RBACService } from './services/RBACService';
// Note: RAGService and ChatService are Premium features, not exported from Core
// Note: DocumentService, ExamService, ReviewService use named exports
export * from './services/DocumentService';
export * from './services/ExamService';
export * from './services/ReviewService';

// ============================================================================
// Components
// ============================================================================

// Re-export layout and admin components
export * from './components/layout';
export * from './components/admin';

// Auth Components - exported with Component suffix to avoid type conflicts
export { LoginForm as LoginFormComponent } from './components/auth/LoginForm';
export { RegisterForm as RegisterFormComponent } from './components/auth/RegisterForm';
export { PasswordResetRequest as PasswordResetRequestComponent } from './components/auth/PasswordResetRequest';
export { PasswordResetConfirm as PasswordResetConfirmComponent } from './components/auth/PasswordResetConfirm';
export { OAuthCallback as OAuthCallbackComponent } from './components/auth/OAuthCallback';
export { AuthPage as AuthPageComponent } from './components/auth/AuthPage';

// Individual component exports
export { default as DocumentUpload } from './components/DocumentUpload';
export { default as DocumentLibrary } from './components/DocumentLibrary';
export { default as QuestionEditor } from './components/QuestionEditor';
export { default as ReviewQueue } from './components/ReviewQueue';
export { default as PackageTierBadge } from './components/layout/PackageTierBadge';
export { default as MarkdownRenderer } from './components/MarkdownRenderer';
export { default as ExamDisplay } from './components/ExamDisplay';
export { default as QuestionReviewCard } from './components/QuestionReviewCard';

// ============================================================================
// Contexts
// ============================================================================

export { AuthProvider, useAuth } from './contexts/AuthContext';
export { GenerationTasksProvider, useGenerationTasks } from './contexts/GenerationTasksContext';

// ============================================================================
// Hooks
// ============================================================================

export { default as useDebounce } from './hooks/useDebounce';
export { useRoleBasedNavigation } from './hooks/useRoleBasedNavigation';

// ============================================================================
// Utils
// ============================================================================

export * from './utils/componentLoader';
export * from './utils/deploymentMode';
