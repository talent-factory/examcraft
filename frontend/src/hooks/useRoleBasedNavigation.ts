/**
 * Role-Based Navigation Hook
 * Provides navigation items based on user roles and permissions.
 *
 * Items are organised into logical, collapsible groups (TF-372). RBAC is
 * applied per item; a group whose items are all filtered out is dropped
 * entirely (header included). The flat `navigationItems` list is derived from
 * the filtered groups and kept for backward compatibility.
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
  excludedRoles?: UserRole[];
  excludeSuperuser?: boolean;
  requiredPermissions?: string[];
  children?: NavigationItem[];
}

/** Closed set of group identifiers — fixed in source, not data-driven. */
export type NavigationGroupId =
  | 'overview'
  | 'content'
  | 'evaluation'
  | 'tools'
  | 'administration';

export interface NavigationGroup {
  /** Stable identifier — the persisted expanded-state value and toggle handle. */
  id: NavigationGroupId;
  label: string;
  items: NavigationItem[];
}

export interface RoleBasedNavigation {
  navigationGroups: NavigationGroup[];
  navigationItems: NavigationItem[];
  hasAccess: (path: string) => boolean;
}

export const useRoleBasedNavigation = (): RoleBasedNavigation => {
  const { user, hasRole, hasPermission } = useAuth();
  const { t } = useTranslation();

  const allNavigationGroups: NavigationGroup[] = useMemo(
    () => [
      {
        id: 'overview',
        label: t('nav.groups.overview'),
        items: [
          {
            label: t('nav.sidebar.dashboard'),
            path: '/dashboard',
            icon: '📊',
          },
          {
            label: t('nav.sidebar.aktivitaeten'),
            path: '/aktivitaeten',
            icon: '🔔',
          },
        ],
      },
      {
        id: 'content',
        label: t('nav.groups.content'),
        items: [
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
            // TF-506: reverse direction of the H1 fixes in Documents.tsx etc. —
            // here the sidebar label follows the page title key, not the other way around
            label: t('pages.review.title'),
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
        ],
      },
      {
        id: 'evaluation',
        label: t('nav.groups.evaluation'),
        items: [
          {
            label: t('nav.sidebar.auswertungen'),
            path: '/auswertungen',
            icon: '📈',
            requiredPermissions: ['submissions:read'],
          },
          {
            label: t('nav.sidebar.auswertungenKlassen'),
            path: '/auswertungen/klassen',
            icon: '🎓',
            requiredPermissions: ['students:manage'],
          },
          {
            label: t('nav.sidebar.auswertungenStudierende'),
            path: '/auswertungen/studierende',
            icon: '👥',
            requiredPermissions: ['students:manage'],
          },
        ],
      },
      {
        id: 'tools',
        label: t('nav.groups.tools'),
        items: [
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
        ],
      },
      {
        id: 'administration',
        label: t('nav.groups.administration'),
        items: [
          {
            // TF-506: reverse direction of the H1 fixes in Documents.tsx etc. —
            // here the sidebar label follows the page title key, not the other way around
            label: t('pages.admin.title'),
            path: '/admin',
            icon: '⚙️',
            requiredRoles: [UserRole.ADMIN],
          },
          {
            label: t('nav.sidebar.tagSettings'),
            path: '/settings/tags',
            icon: '🏷',
            requiredRoles: [UserRole.DOZENT, UserRole.ASSISTANT],
            excludedRoles: [UserRole.ADMIN],
            excludeSuperuser: true,
            requiredPermissions: ['create_questions'],
          },
          {
            label: t('nav.sidebar.competencyFrameworks'),
            path: '/settings/competency-frameworks',
            icon: '🎯',
            // Dozent only: ASSISTANT has no 'create_questions' permission and
            // would be filtered out anyway — the entry would otherwise be dead
            // config clutter. Admin/superuser use the admin panel tab.
            requiredRoles: [UserRole.DOZENT],
            excludedRoles: [UserRole.ADMIN],
            excludeSuperuser: true,
            requiredPermissions: ['create_questions'],
          },
          {
            label: t('nav.sidebar.moodleConnection'),
            path: '/admin/integrations/moodle',
            icon: '🔗',
            requiredRoles: [UserRole.ADMIN],
            requiredPermissions: ['moodle:configure'],
          },
        ],
      },
    ],
    [t],
  );

  const filterNavigationItems = (items: NavigationItem[]): NavigationItem[] => {
    const result: NavigationItem[] = [];
    for (const item of items) {
      if (item.requireSuperuser && !user?.is_superuser) continue;
      if (item.excludeSuperuser && user?.is_superuser) continue;
      if (item.excludedRoles && item.excludedRoles.some(role => hasRole(role))) continue;

      if (item.requiredRoles && item.requiredRoles.length > 0) {
        const hasRequiredRole = user?.is_superuser || item.requiredRoles.some(role => hasRole(role));
        if (!hasRequiredRole) continue;
      }

      if (item.requiredPermissions && item.requiredPermissions.length > 0) {
        const hasRequiredPermission = item.requiredPermissions.some(permission => hasPermission(permission));
        if (!hasRequiredPermission) continue;
      }

      if (item.children) {
        const filteredChildren = filterNavigationItems(item.children);
        if (filteredChildren.length === 0) continue;
        result.push({ ...item, children: filteredChildren });
      } else {
        result.push(item);
      }
    }
    return result;
  };

  // A group with no remaining items after RBAC filtering is hidden entirely,
  // header included (e.g. a Dozent without admin rights sees no empty
  // "Administration" section).
  const navigationGroups = useMemo(() => {
    if (!user) return [];
    return allNavigationGroups
      .map((group) => ({ ...group, items: filterNavigationItems(group.items) }))
      .filter((group) => group.items.length > 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, allNavigationGroups]);

  // Flat list derived from the filtered groups — kept for backward
  // compatibility with consumers that don't care about grouping.
  const navigationItems = useMemo(
    () => navigationGroups.flatMap((group) => group.items),
    [navigationGroups],
  );

  return {
    navigationGroups,
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
