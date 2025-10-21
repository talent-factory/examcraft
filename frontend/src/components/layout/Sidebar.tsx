/**
 * Sidebar Component
 * Role-based navigation sidebar with collapse functionality
 */

import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useRoleBasedNavigation, NavigationItem } from '../../hooks/useRoleBasedNavigation';
import { ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/20/solid';

interface SidebarProps {
  isOpen?: boolean;
  onToggle?: (isOpen: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = true, onToggle }) => {
  const { navigationItems } = useRoleBasedNavigation();
  const location = useLocation();
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const isActivePath = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const toggleExpanded = (path: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedItems(newExpanded);
  };

  const renderIcon = (icon?: string) => {
    if (!icon) return null;
    return <span className="text-lg">{icon}</span>;
  };

  const renderNavItem = (item: NavigationItem, isChild = false) => {
    const isActive = isActivePath(item.path);
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.has(item.path);

    return (
      <div key={item.path}>
        <div className="flex items-center">
          <Link
            to={item.path}
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
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? (
                <ChevronDownIcon className="w-4 h-4" />
              ) : (
                <ChevronRightIcon className="w-4 h-4" />
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

  return (
    <aside
      className={`fixed left-0 top-16 h-screen-minus-nav bg-white border-r border-gray-200 transition-all duration-250 z-40 ${
        isOpen ? 'w-sidebar' : 'w-sidebar-collapsed'
      }`}
    >
      {/* Sidebar Content */}
      <nav className="h-full overflow-y-auto py-4 px-2">
        <div className="space-y-1">
          {navigationItems.map((item) => renderNavItem(item))}
        </div>
      </nav>
    </aside>
  );
};

