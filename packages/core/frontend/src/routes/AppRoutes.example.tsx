/**
 * App Routes Configuration Example
 * Example of how to use route guards with React Router
 *
 * USAGE:
 * 1. Rename this file to AppRoutes.tsx
 * 2. Import in App.tsx: import { AppRoutes } from './routes/AppRoutes';
 * 3. Use in App.tsx: <BrowserRouter><AppRoutes /></BrowserRouter>
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '../contexts/AuthContext';
import { ProtectedRoute, RoleGuard, PermissionGuard, GuestRoute, UnauthorizedPage } from '../components/guards';
import { AppLayout } from '../components/layout';
import { AuthPage, OAuthCallback } from '../components/auth';
import { UserRole } from '../types/auth';

// Placeholder components - replace with actual components
const DashboardPage = () => <div className="p-6"><h1 className="text-2xl font-bold">Dashboard</h1></div>;
const DocumentsPage = () => <div className="p-6"><h1 className="text-2xl font-bold">Documents</h1></div>;
const QuestionGeneratePage = () => <div className="p-6"><h1 className="text-2xl font-bold">Question Generation</h1></div>;
const ReviewQueuePage = () => <div className="p-6"><h1 className="text-2xl font-bold">Review Queue</h1></div>;
const ExamComposerPage = () => <div className="p-6"><h1 className="text-2xl font-bold">Exam Composer</h1></div>;
const PromptsPage = () => <div className="p-6"><h1 className="text-2xl font-bold">Prompt Library</h1></div>;
const ProfilePage = () => <div className="p-6"><h1 className="text-2xl font-bold">Profile</h1></div>;
const AdminUsersPage = () => <div className="p-6"><h1 className="text-2xl font-bold">User Management</h1></div>;
const AdminInstitutionPage = () => <div className="p-6"><h1 className="text-2xl font-bold">Institution Settings</h1></div>;
const AdminAuditPage = () => <div className="p-6"><h1 className="text-2xl font-bold">Audit Logs</h1></div>;
const AdminSubscriptionPage = () => <div className="p-6"><h1 className="text-2xl font-bold">Subscription</h1></div>;

export const AppRoutes: React.FC = () => {
  return (
    <AuthProvider>
      <Routes>
        {/* Public Routes (Guest Only) */}
        <Route
          path="/login"
          element={
            <GuestRoute>
              <AuthPage />
            </GuestRoute>
          }
        />

        {/* OAuth Callback Routes */}
        <Route
          path="/auth/callback"
          element={<OAuthCallback />}
        />

        {/* Protected Routes (Authenticated Users) */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DashboardPage />
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
                  <DocumentsPage />
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
                  <QuestionGeneratePage />
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
                  <ReviewQueuePage />
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
                  <ExamComposerPage />
                </AppLayout>
              </PermissionGuard>
            </ProtectedRoute>
          }
        />

        <Route
          path="/prompts"
          element={
            <ProtectedRoute>
              <RoleGuard allowedRoles={[UserRole.ADMIN, UserRole.DOZENT]}>
                <AppLayout>
                  <PromptsPage />
                </AppLayout>
              </RoleGuard>
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

        {/* Admin Routes (Admin Only) */}
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute>
              <RoleGuard allowedRoles={[UserRole.ADMIN]}>
                <AppLayout>
                  <AdminUsersPage />
                </AppLayout>
              </RoleGuard>
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/institution"
          element={
            <ProtectedRoute>
              <RoleGuard allowedRoles={[UserRole.ADMIN]}>
                <AppLayout>
                  <AdminInstitutionPage />
                </AppLayout>
              </RoleGuard>
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/audit"
          element={
            <ProtectedRoute>
              <RoleGuard allowedRoles={[UserRole.ADMIN]}>
                <AppLayout>
                  <AdminAuditPage />
                </AppLayout>
              </RoleGuard>
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/subscription"
          element={
            <ProtectedRoute>
              <RoleGuard allowedRoles={[UserRole.ADMIN]}>
                <AppLayout>
                  <AdminSubscriptionPage />
                </AppLayout>
              </RoleGuard>
            </ProtectedRoute>
          }
        />

        {/* Error Routes */}
        <Route path="/unauthorized" element={<UnauthorizedPage />} />

        {/* Redirects */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  );
};
