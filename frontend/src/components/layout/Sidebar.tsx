/**
 * Sidebar Component
 * Role-based navigation sidebar with collapsible, grouped sections (TF-372).
 *
 * Items are bundled into logical groups. Section headers toggle their group
 * (they are not routes). On the first visit only the active route's group is
 * open; thereafter the persisted open/closed set is restored from localStorage
 * and the active group is additionally force-opened. The icon-only mode
 * (`isOpen=false`) renders a flat icon list without group headers, unchanged
 * from before.
 */

import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router-dom';
import {
  useRoleBasedNavigation,
  NavigationItem,
  NavigationGroup,
} from '../../hooks/useRoleBasedNavigation';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { SIDEBAR_REVEAL_NAV_EVENT, SidebarRevealNavDetail } from './sidebarNavReveal';

interface SidebarProps {
  isOpen?: boolean;
  onToggle?: (isOpen: boolean) => void;
}

const GROUPS_STORAGE_KEY = 'examcraft.sidebar.expandedGroups';

const readStoredGroups = (): string[] | null => {
  try {
    const raw = window.localStorage.getItem(GROUPS_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Reset cleanly on any shape drift (e.g. a future storage-schema change)
    // rather than silently restoring a partial set.
    return Array.isArray(parsed) && parsed.every((x) => typeof x === 'string')
      ? (parsed as string[])
      : null;
  } catch {
    return null;
  }
};

const writeStoredGroups = (ids: string[]): void => {
  try {
    window.localStorage.setItem(GROUPS_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    /* localStorage unavailable (private mode / quota) — non-fatal. */
  }
};

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = true }) => {
  const { t } = useTranslation();
  const { navigationGroups, navigationItems } = useRoleBasedNavigation();
  const location = useLocation();

  // Expansion state of items that carry children (independent of groups).
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const isActivePath = (path: string, hasChildren: boolean) => {
    if (location.pathname === path) return true;
    return hasChildren && location.pathname.startsWith(path + '/');
  };

  // The group that owns the currently active route — always kept open so the
  // active item stays visible.
  const activeGroupId = useMemo(() => {
    for (const group of navigationGroups) {
      const match = group.items.some((item) =>
        isActivePath(item.path, !!(item.children && item.children.length > 0)),
      );
      if (match) return group.id;
    }
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigationGroups, location.pathname]);

  // Restore persisted open/closed state; fall back to only the active group on
  // first visit.
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => {
    const stored = readStoredGroups();
    if (stored) return new Set(stored);
    return activeGroupId ? new Set([activeGroupId]) : new Set();
  });

  // When the active route changes (or groups load late), make sure its group is
  // open. Additive only — never collapses what the user expanded.
  useEffect(() => {
    if (!activeGroupId) return;
    setExpandedGroups((prev) => {
      if (prev.has(activeGroupId)) return prev;
      const next = new Set(prev);
      next.add(activeGroupId);
      return next;
    });
  }, [activeGroupId]);

  // Persist whenever the set changes.
  useEffect(() => {
    writeStoredGroups([...expandedGroups]);
  }, [expandedGroups]);

  // External reveal requests (TF-604): the onboarding tour highlights nav links
  // by data-testid, but a collapsed group renders no items at all — the tour
  // used to silently skip those steps. Expanding is additive, like the
  // active-route rule above.
  useEffect(() => {
    const handleReveal = (event: Event) => {
      const path = (event as CustomEvent<SidebarRevealNavDetail>).detail?.path;
      if (!path) return;

      let owner: NavigationGroup | undefined;
      let ownerParentPath: string | undefined;
      for (const group of navigationGroups) {
        if (group.items.some((item) => item.path === path)) {
          owner = group;
          break;
        }
        const parentItem = group.items.find((item) =>
          item.children?.some((child) => child.path === path),
        );
        if (parentItem) {
          owner = group;
          ownerParentPath = parentItem.path;
          break;
        }
      }
      // Unknown route -- filtered out by RBAC, the user's nav context not
      // loaded yet, or not in the nav config at all (see sidebarNavReveal.ts
      // for why these can't be told apart here). Logged at debug level: this
      // branch only runs when a Sidebar IS mounted and DID receive the
      // event, so a log here at least confirms that much -- unlike "no
      // Sidebar mounted", which produces no signal anywhere by construction
      // (fire-and-forget event, review fix for observability).
      if (!owner) {
        console.debug('[sidebar] reveal request for unresolved route:', path);
        return;
      }

      const ownerId = owner.id;
      setExpandedGroups((prev) => {
        if (prev.has(ownerId)) return prev;
        const next = new Set(prev);
        next.add(ownerId);
        return next;
      });

      // Review fix: a route nested under item.children needs its parent
      // item's own expandedItems entry too -- the group being open isn't
      // enough, the submenu additionally gates on isExpanded (renderNavItem
      // below). Without this, revealing a child route would open the group,
      // still never render the link, and the caller's poll would time out —
      // reproducing this PR's own bug one level deeper. Currently unreachable
      // (no group in useRoleBasedNavigation defines children yet), kept
      // correct so the reveal mechanism doesn't silently break the day one
      // does.
      if (ownerParentPath) {
        const parentPath = ownerParentPath;
        setExpandedItems((prev) => {
          if (prev.has(parentPath)) return prev;
          const next = new Set(prev);
          next.add(parentPath);
          return next;
        });
      }
    };

    window.addEventListener(SIDEBAR_REVEAL_NAV_EVENT, handleReveal);
    return () => window.removeEventListener(SIDEBAR_REVEAL_NAV_EVENT, handleReveal);
  }, [navigationGroups]);

  // Auto-expand items whose child route is currently open.
  useEffect(() => {
    const autoExpand = new Set<string>();
    for (const item of navigationItems) {
      if (item.children?.some((child) => location.pathname.startsWith(child.path))) {
        autoExpand.add(item.path);
      }
    }
    if (autoExpand.size > 0) {
      setExpandedItems((prev) => new Set([...prev, ...autoExpand]));
    }
  }, [location.pathname, navigationItems]);

  const toggleGroup = (id: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleExpanded = (path: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  // Subtle scroll-fade hint when the list is taller than the viewport.
  const navRef = useRef<HTMLElement>(null);
  const [showScrollFade, setShowScrollFade] = useState(false);
  const updateScrollFade = useCallback(() => {
    const el = navRef.current;
    if (!el) return;
    const remaining = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollFade(remaining > 8);
  }, []);

  useEffect(() => {
    updateScrollFade();
    window.addEventListener('resize', updateScrollFade);
    return () => window.removeEventListener('resize', updateScrollFade);
  }, [updateScrollFade, navigationGroups, navigationItems, expandedGroups, isOpen]);

  const renderIcon = (icon?: string) => {
    if (!icon) return null;
    return <span className="text-lg">{icon}</span>;
  };

  const renderNavItem = (item: NavigationItem, isChild = false) => {
    const hasChildren = !!(item.children && item.children.length > 0);
    const isActive = isActivePath(item.path, hasChildren);
    const isExpanded = expandedItems.has(item.path);

    return (
      <div key={item.path}>
        <div className="flex items-center">
          <Link
            to={item.path}
            data-testid={`nav-${item.path.slice(1).replace(/\//g, '-')}`}
            className={`flex-1 flex items-center px-4 py-3 rounded-lg transition-colors duration-250 ${
              isActive
                ? 'bg-primary-100 text-primary-700 font-medium'
                : 'text-gray-700 hover:bg-gray-100'
            } ${isChild ? 'text-sm' : ''}`}
          >
            {renderIcon(item.icon)}
            {isOpen && <span className="ml-3">{item.label}</span>}
          </Link>

          {hasChildren && isOpen && (
            <button
              onClick={() => toggleExpanded(item.path)}
              className="px-2 py-3 text-gray-500 hover:text-gray-700 transition-colors"
              aria-label={isExpanded ? t('layout.sidebar.collapse') : t('layout.sidebar.expand')}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          )}
        </div>

        {/* Submenu */}
        {hasChildren && isExpanded && isOpen && (
          <div className="ml-4 border-l border-gray-200 mt-1">
            {item.children!.map((child) => renderNavItem(child, true))}
          </div>
        )}
      </div>
    );
  };

  const renderGroup = (group: NavigationGroup) => {
    const isExpanded = expandedGroups.has(group.id);
    return (
      <div key={group.id}>
        <button
          type="button"
          onClick={() => toggleGroup(group.id)}
          data-testid={`nav-group-${group.id}`}
          aria-expanded={isExpanded}
          aria-controls={`nav-group-panel-${group.id}`}
          className="w-full flex items-center justify-between px-4 py-2 text-xs font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-600 transition-colors"
        >
          <span>{group.label}</span>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>

        {isExpanded && (
          <div id={`nav-group-panel-${group.id}`} className="space-y-1 mt-1">
            {group.items.map((item) => renderNavItem(item))}
          </div>
        )}
      </div>
    );
  };

  return (
    <aside
      // Height = viewport minus 64px navbar. Originally configured as
      // 'screen-minus-nav' under theme.extend.minHeight — the wrong theme key
      // for an h-*-utility (that one pulls from theme.height, not minHeight),
      // so 'h-screen-minus-nav' never generated any CSS and the sidebar had
      // no height at all. Fixed as an arbitrary value instead of correcting
      // the theme key, because tailwind.config.js isn't mounted in the dev
      // container (only src/ is) — config changes would otherwise require an
      // image rebuild (TF-506).
      className={`fixed left-0 top-16 h-[calc(100vh_-_64px)] bg-white border-r border-gray-200 transition-all duration-250 z-40 ${
        isOpen ? 'w-sidebar' : 'w-sidebar-collapsed'
      }`}
    >
      {/* Sidebar Content */}
      <div className="h-full flex flex-col">
        <div className="relative flex-1 min-h-0">
          <nav
            ref={navRef}
            onScroll={updateScrollFade}
            // pb-24: bottom breathing room so the last entry stays clear of the
            // version footer / scroll-fade — and of the floating help button (FAB)
            // on narrow viewports where it can overlap the sidebar's lower edge.
            className="h-full overflow-y-auto py-4 px-2 pb-24"
          >
            {isOpen ? (
              <div className="space-y-3">
                {navigationGroups.map((group) => renderGroup(group))}
              </div>
            ) : (
              <div className="space-y-1">
                {navigationItems.map((item) => renderNavItem(item))}
              </div>
            )}
          </nav>

          {/* Subtle fade hinting at more content below the fold. */}
          {isOpen && showScrollFade && (
            <div
              data-testid="sidebar-scroll-fade"
              aria-hidden="true"
              className="pointer-events-none absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent"
            />
          )}
        </div>

        {/* Version Footer */}
        {isOpen && (() => {
          const version = process.env.REACT_APP_VERSION;
          // If the version build arg is missing → fall back to the list view;
          // otherwise link directly to the specific release tag.
          const releasesBase = 'https://github.com/talent-factory/examcraft/releases';
          const href = version ? `${releasesBase}/tag/v${version}` : releasesBase;
          return (
            <div className="px-4 py-3 border-t border-gray-200">
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                v{version || 'dev'}
              </a>
            </div>
          );
        })()}
      </div>
    </aside>
  );
};
