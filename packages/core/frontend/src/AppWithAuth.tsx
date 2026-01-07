/**
 * App with Authentication
 * Main application wrapper with authentication and routing
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute, GuestRoute, PermissionGuard, RoleGuard } from './components/guards';
import { AppLayout } from './components/layout';
import { AuthPage } from './components/auth/AuthPage';
import { OAuthCallback } from './components/auth/OAuthCallback';
import { PasswordResetRequest } from './components/auth/PasswordResetRequest';
import { PasswordResetConfirm } from './components/auth/PasswordResetConfirm';
import { ProfilePage } from './components/profile/ProfilePage';
import { UserManagementPage } from './components/admin/UserManagementPage';
import RoleManagementPage from './components/admin/RoleManagementPage';
import { DocumentChatPage } from './components/DocumentChat/DocumentChatPage';
import { Dashboard } from './pages/Dashboard';
import { Documents } from './pages/Documents';
import { Exams } from './pages/Exams';
import { Review } from './pages/Review';
import { Admin } from './pages/Admin';
import { PromptLibrary } from './pages/PromptLibrary';
import { UserRole } from './types/auth';
import App from './App';
import { AppErrorBoundary, ErrorTestButton } from './components/ErrorBoundary';

// Create a QueryClient instance for TanStack Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

export const AppWithAuth: React.FC = () => {
  return (
    <AppErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            {/* Sentry Test Button (only visible in development) */}
            <ErrorTestButton />
            <Routes>
              {/* Public Routes - Only accessible when NOT authenticated */}
              <Route
                path="/login"
                element={
                  <GuestRoute>
                    <AuthPage />
                  </GuestRoute>
                }
              />
              <Route
                path="/register"
                element={
                  <GuestRoute>
                    <AuthPage defaultTab="register" />
                  </GuestRoute>
                }
              />
              <Route path="/auth/callback" element={<OAuthCallback />} />
              <Route path="/auth/reset-password" element={<PasswordResetRequest />} />
              <Route path="/auth/reset-password/confirm" element={<PasswordResetConfirm />} />

              {/* Protected Routes - Require authentication */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Dashboard />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/documents"
                element={
                  <ProtectedRoute>
                    <PermissionGuard requiredPermissions={['documents:read']}>
                      <AppLayout>
                        <Documents />
                      </AppLayout>
                    </PermissionGuard>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/questions/generate"
                element={
                  <ProtectedRoute>
                    <PermissionGuard requiredPermissions={['questions:create']}>
                      <AppLayout>
                        <Exams />
                      </AppLayout>
                    </PermissionGuard>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/questions/review"
                element={
                  <ProtectedRoute>
                    <PermissionGuard requiredPermissions={['questions:review']}>
                      <AppLayout>
                        <Review />
                      </AppLayout>
                    </PermissionGuard>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/exams/compose"
                element={
                  <ProtectedRoute>
                    <PermissionGuard requiredPermissions={['exams:create']}>
                      <AppLayout>
                        <Exams />
                      </AppLayout>
                    </PermissionGuard>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/chat"
                element={
                  <ProtectedRoute>
                    <PermissionGuard requiredPermissions={['document_chatbot']}>
                      <AppLayout>
                        <DocumentChatPage />
                      </AppLayout>
                    </PermissionGuard>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <ProfilePage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/prompts"
                element={
                  <ProtectedRoute>
                    <RoleGuard allowedRoles={[UserRole.ADMIN, UserRole.DOZENT]}>
                      <AppLayout>
                        <PromptLibrary />
                      </AppLayout>
                    </RoleGuard>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin"
                element={
                  <ProtectedRoute>
                    <RoleGuard allowedRoles={[UserRole.ADMIN]}>
                      <AppLayout>
                        <Admin />
                      </AppLayout>
                    </RoleGuard>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute>
                    <PermissionGuard requiredPermissions={['manage_users']}>
                      <AppLayout>
                        <UserManagementPage />
                      </AppLayout>
                    </PermissionGuard>
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin/roles"
                element={
                  <ProtectedRoute>
                    <RoleGuard allowedRoles={[UserRole.ADMIN]}>
                      <AppLayout>
                        <RoleManagementPage />
                      </AppLayout>
                    </RoleGuard>
                  </ProtectedRoute>
                }
              />

              {/* Redirect root to dashboard */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />

              {/* Redirect unknown routes to dashboard */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </AppErrorBoundary>
  );
};
