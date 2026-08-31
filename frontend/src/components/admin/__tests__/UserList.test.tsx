/**
 * UserList tests (TF-602, TF-743).
 *
 * Scoped to two conditionally-rendered action buttons:
 *  - "Org-Units": rendered when the current user has `manage_org_units`,
 *    but still nested *inside* the coarse `canEdit` gate alongside
 *    Edit/Roles/Activate — see
 *    docs/superpowers/specs/2026-08-11-org-unit-member-assignment-ui-design.md.
 *  - "Impersonate" (TF-743): rendered when the current user has
 *    `users:impersonate` AND the client-side scope pre-filter passes
 *    (SuperAdmin: anyone but themselves; institution admin: non-admin,
 *    non-superuser users of their own institution, excluding themselves) —
 *    genuinely independent of `canEdit`, since a support role granted only
 *    `users:impersonate` (TF-740's opt-in-only permission pattern) must
 *    still see the button even without edit rights. The server enforces the
 *    same scope rule independently (`_is_impersonation_privileged` in
 *    `api/admin.py`) — this filter is UX comfort only.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UserList } from '../UserList';
import AdminService from '../../../services/AdminService';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: { listUsers: jest.fn(), updateUserStatus: jest.fn() },
}));

const mockHasPermission = jest.fn<boolean, [string]>(() => false);
let mockCurrentUser: { id: number; is_superuser: boolean; institution_id: number } | undefined;

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ hasPermission: mockHasPermission, user: mockCurrentUser }),
}));

const mockedAdminService = AdminService as jest.Mocked<typeof AdminService>;

const memberRow = {
  id: 7,
  email: 'member@example.com',
  first_name: 'Max',
  last_name: 'Muster',
  institution_id: 1,
  institution_name: 'Test-Institution',
  roles: [] as string[],
  status: 'active',
  is_superuser: false,
  created_at: '2026-08-07T00:00:00Z',
};

const makeListResponse = (users: typeof memberRow[]) => ({
  users,
  total: users.length,
  page: 1,
  page_size: 20,
  total_pages: 1,
  can_edit: true,
});

const renderList = (overrides: Partial<Parameters<typeof UserList>[0]> = {}) =>
  render(
    <UserList
      onEditUser={jest.fn()}
      onManageRoles={jest.fn()}
      onManageOrgUnits={jest.fn()}
      onImpersonateUser={jest.fn()}
      canEdit
      {...overrides}
    />,
  );

beforeEach(() => {
  jest.clearAllMocks();
  mockCurrentUser = undefined;
  mockedAdminService.listUsers.mockResolvedValue(makeListResponse([memberRow]));
});

describe('UserList — Org-Units button permission gate', () => {
  it('hides the Org-Units button when the user lacks manage_org_units', async () => {
    mockHasPermission.mockReturnValue(false);

    renderList();

    await screen.findByText('Max Muster');
    expect(screen.queryByTestId('ul-btn-org-units-7')).not.toBeInTheDocument();
  });

  it('shows the Org-Units button and calls onManageOrgUnits when the user has manage_org_units', async () => {
    mockHasPermission.mockReturnValue(true);
    const onManageOrgUnits = jest.fn();

    renderList({ onManageOrgUnits });

    const button = await screen.findByTestId('ul-btn-org-units-7');
    button.click();
    expect(onManageOrgUnits).toHaveBeenCalledWith(7);
  });
});

describe('UserList — Impersonate button permission/scope gate (TF-743)', () => {
  it('hides the Impersonate button when the user lacks users:impersonate, even as superuser', async () => {
    mockHasPermission.mockReturnValue(false);
    mockCurrentUser = { id: 1, is_superuser: true, institution_id: 1 };

    renderList();

    await screen.findByText('Max Muster');
    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });

  it('shows the Impersonate button for a SuperAdmin targeting any user and calls onImpersonateUser', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: true, institution_id: 99 }; // different institution — irrelevant for a SuperAdmin
    const onImpersonateUser = jest.fn();

    renderList({ onImpersonateUser });

    const button = await screen.findByTestId('ul-btn-impersonate-7');
    button.click();
    expect(onImpersonateUser).toHaveBeenCalledWith(7);
  });

  it('hides the Impersonate button for the SuperAdmin\'s own row (no self-impersonation)', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 7, is_superuser: true, institution_id: 1 };

    renderList();

    await screen.findByText('Max Muster');
    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });

  it('shows the Impersonate button for an institution admin targeting a non-admin user of the same institution', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: false, institution_id: 1 };

    renderList();

    expect(await screen.findByTestId('ul-btn-impersonate-7')).toBeInTheDocument();
  });

  it('hides the Impersonate button for an institution admin targeting a user of a different institution', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: false, institution_id: 2 };

    renderList();

    await screen.findByText('Max Muster');
    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });

  it('hides the Impersonate button for an institution admin targeting a user with the admin role', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: false, institution_id: 1 };
    mockedAdminService.listUsers.mockResolvedValue(
      makeListResponse([{ ...memberRow, roles: ['admin'] }]),
    );

    renderList();

    await screen.findByText('Max Muster');
    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });

  it('hides the Impersonate button for an institution admin targeting a superuser without the admin role', async () => {
    // The backend's scope check (_is_impersonation_privileged) rejects
    // superusers too, not just the 'admin' role name — this client-side
    // pre-filter mirrors that so the button isn't shown only to 403 on click.
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: false, institution_id: 1 };
    mockedAdminService.listUsers.mockResolvedValue(
      makeListResponse([{ ...memberRow, is_superuser: true }]),
    );

    renderList();

    await screen.findByText('Max Muster');
    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });

  it('shows the Impersonate button even when canEdit is false, for a role granted only users:impersonate', async () => {
    // TF-740's opt-in-only permission pattern: a dedicated support role can
    // hold users:impersonate without also being an institution/super admin
    // (canEdit gates on the admin role name, not this permission) — such a
    // role must still see the button.
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: true, institution_id: 1 };

    renderList({ canEdit: false });

    expect(await screen.findByTestId('ul-btn-impersonate-7')).toBeInTheDocument();
    // The canEdit-gated actions must stay hidden.
    expect(screen.queryByText('Bearbeiten')).not.toBeInTheDocument();
  });

  it('hides the whole actions column when the user has neither canEdit nor users:impersonate', async () => {
    mockHasPermission.mockReturnValue(false);
    mockCurrentUser = { id: 1, is_superuser: true, institution_id: 1 };

    renderList({ canEdit: false });

    await screen.findByText('Max Muster');
    expect(screen.queryByText('Aktionen')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });
});
