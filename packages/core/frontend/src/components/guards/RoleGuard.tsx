/**
 * Role Guard Component
 * Requires specific role(s) to access
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../types/auth';

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles: UserRole[];
  redirectTo?: string;
  fallback?: React.ReactNode;
}

export const RoleGuard: React.FC<RoleGuardProps> = ({
  children,
  allowedRoles,
  redirectTo = '/unauthorized',
  fallback,
}) => {
  const { user, isAuthenticated, isLoading } = useAuth();
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
    console.log('[RoleGuard] Not authenticated:', { isAuthenticated, hasUser: !!user });
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Debug logging
  console.log('[RoleGuard] Checking roles:', {
    userRoles: user.roles?.map(r => r.name),
    allowedRoles,
    isSuperuser: user.is_superuser
  });

  // Check if user has any of the allowed roles
  const hasAllowedRole = user.is_superuser || user.roles?.some(role =>
    allowedRoles.includes(role.name as UserRole)
  );

  // Show fallback or redirect if user doesn't have required role
  if (!hasAllowedRole) {
    console.log('[RoleGuard] Access denied - user does not have required role');
    if (fallback) {
      return <>{fallback}</>;
    }
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  console.log('[RoleGuard] Access granted');
  return <>{children}</>;
};

