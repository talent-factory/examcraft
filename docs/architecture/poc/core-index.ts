/**
 * ExamCraft AI - Core Package Entry Point
 *
 * This file exports all public APIs from the Core package.
 * Premium and Enterprise packages import from this entry point.
 */

// ============================================================================
// Types
// ============================================================================

// Auth Types
export type {
  User,
  Role,
  Institution,
  Session,
  LoginCredentials,
  RegisterData,
  AuthResponse,
  TokenPayload,
} from './types/auth';

// Document Types
export type {
  Document,
  DocumentMetadata,
  DocumentChunk,
  DocumentUploadRequest,
  DocumentUploadResponse,
  RAGExamRequest,
  RAGExamResponse,
} from './types/document';

// Prompt Types
export type {
  Prompt,
  PromptTemplate,
  PromptVariable,
  PromptCategory,
} from './types/prompt';

// Question Types
export type {
  Question,
  QuestionType,
  QuestionDifficulty,
  QuestionReview,
  QuestionReviewStatus,
} from './types/question';

// ============================================================================
// Services
// ============================================================================

export { AuthService } from './services/AuthService';
export { DocumentService } from './services/DocumentService';
export { PromptService } from './services/PromptService';
export { QuestionService } from './services/QuestionService';

// ============================================================================
// Components
// ============================================================================

// Layout Components
export { default as Layout } from './components/layout/Layout';
export { default as Navigation } from './components/layout/Navigation';
export { default as Sidebar } from './components/layout/Sidebar';

// Auth Components
export { default as LoginForm } from './components/auth/LoginForm';
export { default as RegisterForm } from './components/auth/RegisterForm';
export { default as AuthPage } from './components/auth/AuthPage';

// Common Components
export { default as Button } from './components/common/Button';
export { default as Card } from './components/common/Card';
export { default as Input } from './components/common/Input';
export { default as Select } from './components/common/Select';
export { default as Modal } from './components/common/Modal';

// Admin Components
export { default as UserManagement } from './components/admin/UserManagement';
export { default as InstitutionManagement } from './components/admin/InstitutionManagement';
export { default as PromptLibrary } from './components/admin/PromptLibrary';
export { default as PromptEditor } from './components/admin/PromptEditor';

// ============================================================================
// Contexts
// ============================================================================

export { AuthProvider, useAuth } from './contexts/AuthContext';

// ============================================================================
// Utils
// ============================================================================

export { formatDate, parseDate } from './utils/dateUtils';
export { validateEmail, validatePassword } from './utils/validation';
export { cn } from './utils/classNames';
export { apiClient } from './utils/apiClient';

// ============================================================================
// Constants
// ============================================================================

export { API_BASE_URL, API_ENDPOINTS } from './constants/api';
export { ROUTES } from './constants/routes';
export { SUBSCRIPTION_TIERS } from './constants/subscriptions';
