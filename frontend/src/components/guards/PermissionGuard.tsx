/**
 * Permission Guard Component
 * Requires specific permission(s) to access
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface PermissionGuardProps {
  children: React.ReactNode;
  requiredPermissions: string[];
  requireAll?: boolean; // If true, user must have ALL permissions. If false, user needs ANY permission.
  redirectTo?: string;
  fallback?: React.ReactNode;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  children,
  requiredPermissions,
  requireAll = false,
  redirectTo = '/unauthorized',
  fallback,
}) => {
  const { user, isAuthenticated, isLoading, hasPermission } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check permissions
  const hasRequiredPermissions = requireAll
    ? requiredPermissions.every(permission => hasPermission(permission))
    : requiredPermissions.some(permission => hasPermission(permission));

  // Show fallback or redirect if user doesn't have required permissions
  if (!hasRequiredPermissions) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

