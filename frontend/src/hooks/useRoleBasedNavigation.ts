/**
 * Role-Based Navigation Hook
 * Provides navigation items based on user roles and permissions
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();

  const allNavigationItems: NavigationItem[] = useMemo(() => [
    {
      label: t('nav.sidebar.dashboard'),
      path: '/dashboard',
      icon: '📊',
    },
    {
      label: t('nav.sidebar.documents'),
      path: '/documents',
      icon: '📄',
      requiredPermissions: ['documents:read'],
    },
    {
      label: t('nav.sidebar.questionGeneration'),
      path: '/questions/generate',
      icon: '✨',
      requiredPermissions: ['create_questions'],
    },
    {
      label: t('nav.sidebar.reviewQueue'),
      path: '/questions/review',
      icon: '✅',
      requiredPermissions: ['review_questions'],
    },
    {
      label: t('nav.sidebar.examComposer'),
      path: '/exams/compose',
      icon: '📝',
      requiredPermissions: ['create_exams'],
    },
    {
      label: t('nav.sidebar.documentChat'),
      path: '/chat',
      icon: '💬',
      requiredPermissions: ['document_chatbot'],
    },
    {
      label: t('nav.sidebar.promptLibrary'),
      path: '/prompts',
      icon: '💬',
      requiredRoles: [UserRole.ADMIN, UserRole.DOZENT],
      requiredPermissions: ['prompt_templates'],
    },
    {
      label: t('nav.sidebar.admin'),
      path: '/admin',
      icon: '⚙️',
      requiredRoles: [UserRole.ADMIN],
    },
  ], [t]);

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
