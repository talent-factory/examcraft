/**
 * Role-Based Navigation Hook
 * Provides navigation items based on user roles and permissions
 */

import { useMemo } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { UserRole } from '../types/auth';

export interface NavigationItem {
  label: string;
  path: string;
  icon?: string;
  requireSuperuser?: boolean;
  requiredRoles?: UserRole[];
  requiredPermissions?: string[];
  children?: NavigationItem[];
}

export const useRoleBasedNavigation = () => {
  const { user, hasRole, hasPermission } = useAuth();

  const allNavigationItems: NavigationItem[] = useMemo(() => [
    {
      label: 'Dashboard',
      path: '/dashboard',
      icon: '📊',
    },
    {
      label: 'Documents',
      path: '/documents',
      icon: '📄',
      requiredPermissions: ['documents:read'],
    },
    {
      label: 'Question Generation',
      path: '/questions/generate',
      icon: '✨',
      requiredPermissions: ['questions:create'],
    },
    {
      label: 'Review Queue',
      path: '/questions/review',
      icon: '✅',
      requiredPermissions: ['questions:review'],
    },
    {
      label: 'Exam Composer',
      path: '/exams/compose',
      icon: '📝',
      requiredPermissions: ['exams:create'],
    },
    {
      label: 'Document Chat',
      path: '/chat',
      icon: '💬',
      requiredPermissions: ['document_chatbot'],
    },
    {
      label: 'Prompt Library',
      path: '/prompts',
      icon: '💬',
      requiredRoles: [UserRole.ADMIN, UserRole.DOZENT],
    },
    {
      label: 'Admin',
      path: '/admin',
      icon: '⚙️',
      requiredRoles: [UserRole.ADMIN],
      children: [
        {
          label: 'User Management',
          path: '/admin/users',
          icon: '👥',
          requiredPermissions: ['manage_users'],
        },
        {
          label: 'Role Management',
          path: '/admin/roles',
          icon: '🔐',
          requireSuperuser: true,
        },
        {
          label: 'Institution Settings',
          path: '/admin/institution',
          icon: '🏛️',
          requireSuperuser: true,
        },
        {
          label: 'Audit Logs',
          path: '/admin/audit',
          icon: '📋',
          requiredRoles: [UserRole.ADMIN],
        },
        {
          label: 'Subscription',
          path: '/admin/subscription',
          icon: '💳',
          requiredRoles: [UserRole.ADMIN],
        },
      ],
    },
    {
      label: 'Pricing',
      path: '/billing',
      icon: '💳',
    },
    {
      label: 'Profile',
      path: '/profile',
      icon: '👤',
    },
  ], []);

  const filterNavigationItems = (items: NavigationItem[]): NavigationItem[] => {
    return items.filter(item => {
      // Check superuser-only items
      if (item.requireSuperuser && !user?.is_superuser) return false;

      // Check role requirements
      if (item.requiredRoles && item.requiredRoles.length > 0) {
        const hasRequiredRole = user?.is_superuser || item.requiredRoles.some(role => hasRole(role));
        if (!hasRequiredRole) return false;
      }

      // Check permission requirements
      if (item.requiredPermissions && item.requiredPermissions.length > 0) {
        const hasRequiredPermission = item.requiredPermissions.some(permission => hasPermission(permission));
        if (!hasRequiredPermission) return false;
      }

      // Filter children recursively
      if (item.children) {
        item.children = filterNavigationItems(item.children);
        // Remove parent if all children are filtered out
        if (item.children.length === 0) return false;
      }

      return true;
    });
  };

  const navigationItems = useMemo(() => {
    if (!user) return [];
    return filterNavigationItems(allNavigationItems);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, allNavigationItems]);

  return {
    navigationItems,
    hasAccess: (path: string) => {
      const findItem = (items: NavigationItem[]): boolean => {
        for (const item of items) {
          if (item.path === path) return true;
          if (item.children && findItem(item.children)) return true;
        }
        return false;
      };
      return findItem(navigationItems);
    },
  };
};
