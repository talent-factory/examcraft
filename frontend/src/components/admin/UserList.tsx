/**
 * User List Component
 * Displays all users in a table with pagination, search, and filters
 */

import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { Building2, MoreVertical, Pencil, Power, LogIn, Shield } from 'lucide-react';
import { getDateLocale } from '../../utils/dateLocale';
import AdminService, { UserListItem, ListUsersParams } from '../../services/AdminService';
import { translateError } from '../../errors';
import { UserStatus } from '../../types/auth';
import { useAuth } from '../../contexts/AuthContext';

interface UserListProps {
  onEditUser: (userId: number) => void;
  onManageRoles: (userId: number) => void;
  onManageOrgUnits: (userId: number) => void;
  onImpersonateUser: (userId: number) => void;
  onRefresh?: () => void;
  canEdit?: boolean;
}

export const UserList: React.FC<UserListProps> = ({
  onEditUser,
  onManageRoles,
  onManageOrgUnits,
  onImpersonateUser,
  onRefresh,
  canEdit = false,
}) => {
  const { t, i18n } = useTranslation();
  const { hasPermission, user: currentUser } = useAuth();
  const canManageOrgUnits = hasPermission('manage_org_units');
  const canImpersonate = hasPermission('users:impersonate');

  /**
   * Client-side pre-filter only (UX comfort) — the actual scope rule is
   * enforced server-side by `_is_impersonation_privileged` in
   * `api/admin.py`, which additionally checks the target's *permissions*,
   * not just their role name. This mirrors just the role-name check, plus
   * the institution/self-exclusion rules the ticket calls out explicitly.
   */
  const canImpersonateUser = (target: UserListItem): boolean => {
    if (!canImpersonate || !currentUser || target.id === currentUser.id) return false;
    if (currentUser.is_superuser) return true;
    return (
      target.institution_id === currentUser.institution_id &&
      !target.roles.includes('admin') &&
      !target.is_superuser
    );
  };
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  // Filter state
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Actions kebab menu (TF-801): at most one row's menu is open at a time.
  // The menu itself is rendered in a portal (see the JSX below) at a fixed,
  // viewport-clamped position computed by the layout effect further down —
  // it would otherwise be clipped by the table's overflow-hidden /
  // overflow-x-auto ancestors (needed for the card's rounded corners and
  // for horizontal scrolling on narrow viewports) whenever it opened from
  // one of the last rows on a page.
  const [openActionsUserId, setOpenActionsUserId] = useState<number | null>(null);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const actionsTriggerRef = useRef<HTMLButtonElement>(null);
  const actionsMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 500);

    return () => clearTimeout(timer);
  }, [search]);

  // Close the open actions menu on an outside click, Escape, or
  // scroll/resize (the portaled menu's position is computed once at open
  // time — see the layout effect below — and would otherwise drift out of
  // place) — mirrors the institution/platform scope-switcher pattern in
  // pages/Admin.tsx, extended for the portal + viewport-relative
  // positioning this menu needs that the scope switcher doesn't.
  useEffect(() => {
    if (openActionsUserId === null) return undefined;

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      const insideTrigger = actionsTriggerRef.current?.contains(target);
      const insideMenu = actionsMenuRef.current?.contains(target);
      if (!insideTrigger && !insideMenu) {
        setOpenActionsUserId(null);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpenActionsUserId(null);
        actionsTriggerRef.current?.focus();
      }
    };
    const handleScrollOrResize = () => setOpenActionsUserId(null);

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('scroll', handleScrollOrResize, true);
    window.addEventListener('resize', handleScrollOrResize);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('scroll', handleScrollOrResize, true);
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [openActionsUserId]);

  // Position the portaled menu against its trigger, flipping upward when
  // there isn't room below the viewport and clamping horizontally so it
  // never renders off-screen. Runs as a layout effect (before paint) so the
  // menu's real, just-rendered dimensions (not an estimate) are available
  // and no positioned-at-(0,0) frame is ever visible.
  useLayoutEffect(() => {
    if (openActionsUserId === null) {
      setMenuPosition(null);
      return;
    }
    const trigger = actionsTriggerRef.current;
    if (!trigger) return;

    const triggerRect = trigger.getBoundingClientRect();
    const menuHeight = actionsMenuRef.current?.offsetHeight || 0;
    const menuWidth = actionsMenuRef.current?.offsetWidth || 208; // w-52
    const gap = 4;

    const openUpward = window.innerHeight - triggerRect.bottom < menuHeight + gap
      && triggerRect.top > menuHeight + gap;
    const top = openUpward ? triggerRect.top - menuHeight - gap : triggerRect.bottom + gap;
    const left = Math.min(
      Math.max(8, triggerRect.right - menuWidth),
      window.innerWidth - menuWidth - 8,
    );

    setMenuPosition({ top, left });

    // Move focus into the menu when it opens (WAI-ARIA menu-button
    // pattern) — keeps keyboard users from having to tab back in.
    actionsMenuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
  }, [openActionsUserId]);

  /** Arrow-key/Home/End roving focus within the open menu (Escape is handled globally above). */
  const handleMenuKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const items = Array.from(
      actionsMenuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [],
    );
    if (items.length === 0) return;
    const currentIndex = items.indexOf(document.activeElement as HTMLElement);

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      items[(currentIndex + 1 + items.length) % items.length].focus();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      items[(currentIndex - 1 + items.length) % items.length].focus();
    } else if (event.key === 'Home') {
      event.preventDefault();
      items[0].focus();
    } else if (event.key === 'End') {
      event.preventDefault();
      items[items.length - 1].focus();
    }
  };

  /** Closes the menu and returns focus to its trigger — used by every menu-item action. */
  const closeActionsMenu = () => {
    setOpenActionsUserId(null);
    actionsTriggerRef.current?.focus();
  };

  useEffect(() => {
    loadUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, debouncedSearch, roleFilter, statusFilter]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: ListUsersParams = {
        page,
        page_size: pageSize,
      };

      if (debouncedSearch) params.search = debouncedSearch;
      if (roleFilter) params.role = roleFilter;
      if (statusFilter) params.status = statusFilter;

      const response = await AdminService.listUsers(params);

      setUsers(response.users);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (err) {
      setError(translateError(err, t, 'admin.userList.failedLoad'));
    } finally {
      setLoading(false);
    }
  };

  const handleStatusToggle = async (userId: number, currentStatus: string) => {
    try {
      const newStatus = currentStatus === UserStatus.ACTIVE
        ? UserStatus.INACTIVE
        : UserStatus.ACTIVE;

      await AdminService.updateUserStatus(userId, newStatus);
      await loadUsers();
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(translateError(err, t, 'admin.userList.failedStatus'));
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return t('admin.userList.never');
    return new Date(dateString).toLocaleDateString(getDateLocale(i18n.language), {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case UserStatus.ACTIVE:
        return 'bg-green-100 text-green-800';
      case UserStatus.INACTIVE:
        return 'bg-gray-100 text-gray-800';
      case UserStatus.SUSPENDED:
        return 'bg-red-100 text-red-800';
      case UserStatus.PENDING:
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading && users.length === 0) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('admin.userList.searchLabel')}
            </label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('admin.userList.searchPlaceholder')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Role Filter */}
          <div>
            <label htmlFor="role-filter" className="block text-sm font-medium text-gray-700 mb-1">
              {t('admin.userList.roleLabel')}
            </label>
            <select
              id="role-filter"
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">{t('admin.userList.allRoles')}</option>
              <option value="admin">{t('admin.userList.roleAdmin')}</option>
              <option value="dozent">{t('admin.userList.roleDozent')}</option>
              <option value="assistant">{t('admin.userList.roleAssistant')}</option>
              <option value="viewer">{t('admin.userList.roleViewer')}</option>
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label htmlFor="status-filter" className="block text-sm font-medium text-gray-700 mb-1">
              {t('admin.userList.statusLabel')}
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">{t('admin.userList.allStatus')}</option>
              <option value="active">{t('admin.userList.statusActive')}</option>
              <option value="inactive">{t('admin.userList.statusInactive')}</option>
              <option value="suspended">{t('admin.userList.statusSuspended')}</option>
              <option value="pending">{t('admin.userList.statusPending')}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* User Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {t('admin.userList.colUser')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {t('admin.userList.colInstitution')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {t('admin.userList.colRoles')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {t('admin.userList.colStatus')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {t('admin.userList.colLastLogin')}
                </th>
                {(canEdit || canImpersonate) && (
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {t('admin.userList.colActions')}
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {user.first_name} {user.last_name}
                          {user.is_superuser && (
                            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                              {t('admin.userList.superuser')}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{user.institution_name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((role, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                        >
                          {role}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(user.status)}`}>
                      {user.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(user.last_login_at)}
                  </td>
                  {(canEdit || canImpersonateUser(user)) && (
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {/* TF-801: all row actions collapsed behind a single
                          kebab trigger + dropdown — these are used rarely,
                          and four-to-five always-visible, differently
                          colored text links made the table noisy. The
                          dropdown itself is rendered in a portal (below)
                          at a fixed, viewport-clamped position — see the
                          positioning layout effect above — instead of
                          absolutely inside this cell, so it isn't clipped
                          by the table's overflow-hidden/overflow-x-auto
                          ancestors for rows near the bottom of a page. */}
                      <button
                        type="button"
                        ref={openActionsUserId === user.id ? actionsTriggerRef : undefined}
                        onClick={() => setOpenActionsUserId((prev) => (prev === user.id ? null : user.id))}
                        aria-haspopup="menu"
                        aria-expanded={openActionsUserId === user.id}
                        aria-controls={openActionsUserId === user.id ? `ul-actions-menu-${user.id}` : undefined}
                        aria-label={t('admin.userList.actionsMenuLabel', { name: `${user.first_name} ${user.last_name}` })}
                        data-testid={`ul-actions-menu-trigger-${user.id}`}
                        className={`inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 ${
                          openActionsUserId === user.id ? 'bg-gray-100 text-gray-700' : ''
                        }`}
                      >
                        <MoreVertical className="w-[18px] h-[18px]" aria-hidden="true" />
                      </button>

                      {openActionsUserId === user.id && createPortal(
                        <div
                          id={`ul-actions-menu-${user.id}`}
                          role="menu"
                          aria-label={t('admin.userList.actionsMenuLabel', { name: `${user.first_name} ${user.last_name}` })}
                          ref={actionsMenuRef}
                          onKeyDown={handleMenuKeyDown}
                          style={{
                            position: 'fixed',
                            top: menuPosition?.top ?? 0,
                            left: menuPosition?.left ?? 0,
                            visibility: menuPosition ? 'visible' : 'hidden',
                          }}
                          className="z-20 w-52 bg-white border border-gray-200 rounded-lg shadow-lg p-1.5 text-left"
                        >
                          {canEdit && (
                            <>
                              <button
                                type="button"
                                role="menuitem"
                                onClick={() => {
                                  closeActionsMenu();
                                  onEditUser(user.id);
                                }}
                                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-gray-700 hover:bg-gray-50"
                              >
                                <Pencil className="w-4 h-4" aria-hidden="true" />
                                {t('admin.userList.btnEdit')}
                              </button>
                              <button
                                type="button"
                                role="menuitem"
                                onClick={() => {
                                  closeActionsMenu();
                                  onManageRoles(user.id);
                                }}
                                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-gray-700 hover:bg-gray-50"
                              >
                                <Shield className="w-4 h-4" aria-hidden="true" />
                                {t('admin.userList.btnRoles')}
                              </button>
                              {canManageOrgUnits && (
                                <button
                                  type="button"
                                  role="menuitem"
                                  onClick={() => {
                                    closeActionsMenu();
                                    onManageOrgUnits(user.id);
                                  }}
                                  className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-gray-700 hover:bg-gray-50"
                                  data-testid={`ul-btn-org-units-${user.id}`}
                                >
                                  <Building2 className="w-4 h-4" aria-hidden="true" />
                                  {t('admin.userList.btnOrgUnits')}
                                </button>
                              )}
                              <div className="h-px bg-gray-100 my-1" />
                              <button
                                type="button"
                                role="menuitem"
                                onClick={() => {
                                  closeActionsMenu();
                                  handleStatusToggle(user.id, user.status);
                                }}
                                className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-sm hover:bg-gray-50 ${
                                  user.status === UserStatus.ACTIVE ? 'text-red-600' : 'text-green-600'
                                }`}
                                data-testid={`ul-btn-toggle-status-${user.id}`}
                              >
                                <Power className="w-4 h-4" aria-hidden="true" />
                                {user.status === UserStatus.ACTIVE ? t('admin.userList.btnDeactivate') : t('admin.userList.btnActivate')}
                              </button>
                            </>
                          )}
                          {/* TF-743: impersonation is its own permission
                              (users:impersonate), deliberately not folded
                              into the coarse canEdit prop — a support role
                              granted only this permission must still see
                              the button. */}
                          {canImpersonateUser(user) && (
                            <>
                              {canEdit && <div className="h-px bg-gray-100 my-1" />}
                              <button
                                type="button"
                                role="menuitem"
                                onClick={() => {
                                  closeActionsMenu();
                                  onImpersonateUser(user.id);
                                }}
                                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-sm text-orange-600 hover:bg-orange-50"
                                data-testid={`ul-btn-impersonate-${user.id}`}
                              >
                                <LogIn className="w-4 h-4" aria-hidden="true" />
                                {t('admin.userList.btnImpersonate')}
                              </button>
                            </>
                          )}
                        </div>,
                        document.body,
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
          <div className="flex-1 flex justify-between sm:hidden">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('admin.userList.paginationPrevious')}
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('admin.userList.paginationNext')}
            </button>
          </div>
          <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                {t('admin.userList.paginationShowing', { from: (page - 1) * pageSize + 1, to: Math.min(page * pageSize, total), total })}
              </p>
            </div>
            <div>
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('admin.userList.paginationPrevious')}
                </button>
                <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">
                  {t('admin.userList.paginationPage', { page, total: totalPages })}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('admin.userList.paginationNext')}
                </button>
              </nav>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
