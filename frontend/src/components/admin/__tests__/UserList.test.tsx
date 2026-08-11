/**
 * UserList tests (TF-602).
 *
 * Scoped to the new "Org-Units" action button: it must only render when
 * the current user has the `manage_org_units` permission, independent of
 * `canEdit` (which gates Edit/Roles/Activate and is a coarser check — see
 * docs/superpowers/specs/2026-08-11-org-unit-member-assignment-ui-design.md).
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UserList } from '../UserList';
import AdminService from '../../../services/AdminService';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: { listUsers: jest.fn(), updateUserStatus: jest.fn() },
}));

const mockHasPermission = jest.fn<boolean, [string]>(() => false);
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ hasPermission: mockHasPermission }),
}));

const mockedAdminService = AdminService as jest.Mocked<typeof AdminService>;

const listResponse = {
  users: [
    {
      id: 7,
      email: 'member@example.com',
      first_name: 'Max',
      last_name: 'Muster',
      institution_id: 1,
      institution_name: 'Test-Institution',
      roles: [],
      status: 'active',
      is_superuser: false,
      created_at: '2026-08-07T00:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
  can_edit: true,
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedAdminService.listUsers.mockResolvedValue(listResponse);
});

describe('UserList — Org-Units button permission gate', () => {
  it('hides the Org-Units button when the user lacks manage_org_units', async () => {
    mockHasPermission.mockReturnValue(false);

    render(
      <UserList
        onEditUser={jest.fn()}
        onManageRoles={jest.fn()}
        onManageOrgUnits={jest.fn()}
        canEdit
      />,
    );

    await waitFor(() => expect(screen.queryByText('Max Muster')).toBeInTheDocument());
    expect(screen.queryByTestId('ul-btn-org-units-7')).not.toBeInTheDocument();
  });

  it('shows the Org-Units button and calls onManageOrgUnits when the user has manage_org_units', async () => {
    mockHasPermission.mockReturnValue(true);
    const onManageOrgUnits = jest.fn();

    render(
      <UserList
        onEditUser={jest.fn()}
        onManageRoles={jest.fn()}
        onManageOrgUnits={onManageOrgUnits}
        canEdit
      />,
    );

    const button = await screen.findByTestId('ul-btn-org-units-7');
    button.click();
    expect(onManageOrgUnits).toHaveBeenCalledWith(7);
  });
});
