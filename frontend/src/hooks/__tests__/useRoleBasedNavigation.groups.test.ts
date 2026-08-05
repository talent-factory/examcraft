/**
 * useRoleBasedNavigation — grouping behaviour (TF-372)
 *
 * Verifies that navigation items are bundled into the five logical groups,
 * that RBAC is applied per item, and that a group whose items are all filtered
 * out is dropped entirely (header included).
 *
 * react-i18next is globally mocked in setupTests to resolve real DE strings,
 * so group/item labels here are the German translations.
 */

import { renderHook } from '@testing-library/react';
import { useRoleBasedNavigation } from '../useRoleBasedNavigation';
import { UserRole } from '../../types/auth';

// Controllable auth mock.
let mockUser: { is_superuser: boolean } | null = { is_superuser: false };
const mockHasRole = jest.fn();
const mockHasPermission = jest.fn();

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    hasRole: mockHasRole,
    hasPermission: mockHasPermission,
  }),
}));

const roleIs =
  (...roles: UserRole[]) =>
  (role: UserRole) =>
    roles.includes(role);

const permIn =
  (...perms: string[]) =>
  (perm: string) =>
    perms.includes(perm);

beforeEach(() => {
  mockUser = { is_superuser: false };
  mockHasRole.mockReset().mockReturnValue(false);
  mockHasPermission.mockReset().mockReturnValue(false);
});

const groupIds = () =>
  renderHook(() => useRoleBasedNavigation()).result.current.navigationGroups.map((g) => g.id);

describe('useRoleBasedNavigation - grouping', () => {
  it('returns an empty list when there is no user', () => {
    mockUser = null;
    const { result } = renderHook(() => useRoleBasedNavigation());
    expect(result.current.navigationGroups).toEqual([]);
    expect(result.current.navigationItems).toEqual([]);
  });

  it('exposes the five groups in order for a superuser', () => {
    mockUser = { is_superuser: true };
    mockHasPermission.mockReturnValue(true);

    expect(groupIds()).toEqual([
      'overview',
      'content',
      'evaluation',
      'tools',
      'administration',
    ]);
  });

  it('keeps the active RBAC fields on each grouped item', () => {
    mockUser = { is_superuser: true };
    mockHasPermission.mockReturnValue(true);

    const { result } = renderHook(() => useRoleBasedNavigation());
    const content = result.current.navigationGroups.find((g) => g.id === 'content');
    const docs = content?.items.find((i) => i.path === '/documents');

    expect(docs?.requiredPermissions).toEqual(['documents:read']);
  });

  it('hides groups that are empty after per-item RBAC filtering', () => {
    // Viewer with only documents:read — evaluation/tools/administration empty.
    mockHasPermission.mockImplementation(permIn('documents:read'));

    const { result } = renderHook(() => useRoleBasedNavigation());
    const ids = result.current.navigationGroups.map((g) => g.id);

    expect(ids).toEqual(['overview', 'content']);
    expect(ids).not.toContain('evaluation');
    expect(ids).not.toContain('tools');
    expect(ids).not.toContain('administration');
  });

  it('filters per item inside a surviving group', () => {
    // Dozent with submissions:read but not students:manage → evaluation keeps
    // only "Auswertungen".
    mockHasRole.mockImplementation(roleIs(UserRole.DOZENT));
    mockHasPermission.mockImplementation(permIn('submissions:read'));

    const { result } = renderHook(() => useRoleBasedNavigation());
    const evaluation = result.current.navigationGroups.find((g) => g.id === 'evaluation');

    expect(evaluation).toBeDefined();
    expect(evaluation?.items.map((i) => i.path)).toEqual(['/auswertungen']);
  });

  it('hides the administration group for a dozent without admin rights', () => {
    // Dozent, no permissions at all → admin/tagSettings/moodle all filtered.
    mockHasRole.mockImplementation(roleIs(UserRole.DOZENT));
    mockHasPermission.mockReturnValue(false);

    expect(groupIds()).not.toContain('administration');
  });

  it('derives the flat navigationItems from the visible groups', () => {
    mockHasPermission.mockImplementation(permIn('documents:read'));

    const { result } = renderHook(() => useRoleBasedNavigation());
    const flatFromGroups = result.current.navigationGroups.flatMap((g) => g.items);

    expect(result.current.navigationItems).toEqual(flatFromGroups);
    expect(result.current.navigationItems.map((i) => i.path)).toEqual([
      '/dashboard',
      '/aktivitaeten',
      '/documents',
    ]);
  });

  it('hasAccess reflects the filtered item set', () => {
    mockHasPermission.mockImplementation(permIn('documents:read'));

    const { result } = renderHook(() => useRoleBasedNavigation());
    expect(result.current.hasAccess('/documents')).toBe(true);
    expect(result.current.hasAccess('/admin')).toBe(false);
  });

  it('resolves the admin and review labels from their page-title i18n keys (TF-506)', () => {
    // Regression: these labels previously came from nav.sidebar.admin /
    // nav.sidebar.reviewQueue, which had drifted from the H1s the /admin and
    // /questions/review pages actually render. They now share
    // pages.admin.title / pages.review.title, so this catches either key
    // reverting or being mistyped.
    mockUser = { is_superuser: true };
    mockHasPermission.mockReturnValue(true);

    const { result } = renderHook(() => useRoleBasedNavigation());
    const byPath = (path: string) => result.current.navigationItems.find((i) => i.path === path);

    expect(byPath('/admin')?.label).toBe('Admin-Panel');
    expect(byPath('/questions/review')?.label).toBe('Fragen-Review');
  });
});
