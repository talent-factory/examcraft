/**
 * App with Authentication
 * Main application wrapper with authentication and routing
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute, GuestRoute } from './components/guards';
import { AppLayout } from './components/layout';
import { AuthPage } from './components/auth/AuthPage';
import { OAuthCallback } from './components/auth/OAuthCallback';
import { PasswordResetRequest } from './components/auth/PasswordResetRequest';
import { PasswordResetConfirm } from './components/auth/PasswordResetConfirm';
import { ProfilePage } from './components/profile/ProfilePage';
import App from './App';

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
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
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
              path="/*"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Routes>
                      {/* Main App */}
                      <Route path="/" element={<App />} />
                      
                      {/* Profile */}
                      <Route path="/profile" element={<ProfilePage />} />
                      
                      {/* Redirect unknown routes to home */}
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

