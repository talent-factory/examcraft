/**
 * RoleAssignmentDialog tests (TF-621).
 *
 * TF-621: institution-admins previously saw the contradictory
 * "Keine Rollen zugewiesen" / "Alle Rollen zugewiesen" fallback text
 * alongside the error banner whenever loading the roles catalog failed
 * (e.g. the pre-fix 403 from GET /api/admin/roles). These tests pin the
 * fixed behaviour: on a load failure, only the error banner renders —
 * the "Current Roles" / "Available Roles" sections are hidden instead of
 * showing misleading empty-state copy.
 *
 * They also pin a follow-up fix: the role sections must stay visible when
 * a later assign/remove *action* fails (as opposed to the initial catalog
 * load) — at that point `user`/`allRoles` are still valid and the admin
 * needs to see them to retry, not just an error banner.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { RoleAssignmentDialog } from '../RoleAssignmentDialog';
import AdminService from '../../../services/AdminService';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: {
    getUser: jest.fn(),
    listRoles: jest.fn(),
    assignRole: jest.fn(),
    removeRole: jest.fn(),
  },
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const mockUser = {
  id: 42,
  email: 'user@bwz-lyss.example',
  first_name: 'Test',
  last_name: 'User',
  institution_id: 1,
  institution_name: 'BWZ Lyss',
  roles: [
    {
      id: 2,
      name: 'dozent',
      display_name: 'Dozent',
      description: null,
      permissions: [],
      is_system_role: true,
      created_at: '2026-01-01',
    },
  ],
  status: 'active',
  is_superuser: false,
  created_at: '2026-01-01',
};

const mockRoles = [
  mockUser.roles[0],
  {
    id: 3,
    name: 'assistant',
    display_name: 'Assistant',
    description: null,
    permissions: [],
    is_system_role: true,
    created_at: '2026-01-01',
  },
];

describe('RoleAssignmentDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('does not render when isOpen=false', () => {
    render(
      <RoleAssignmentDialog
        userId={42}
        isOpen={false}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );
    expect(screen.queryByText('admin.roleAssignment.title')).toBeNull();
  });

  it('renders current and available roles on successful load', async () => {
    (AdminService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (AdminService.listRoles as jest.Mock).mockResolvedValue(mockRoles);

    render(
      <RoleAssignmentDialog
        userId={42}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );

    expect(await screen.findByText('Dozent')).toBeInTheDocument();
    expect(screen.getByText('Assistant')).toBeInTheDocument();
    expect(screen.queryByText('admin.roleAssignment.noRoles')).toBeNull();
    expect(screen.queryByText('admin.roleAssignment.allRolesAssigned')).toBeNull();
  });

  it('TF-621: on a roles-catalog fetch failure, shows only the error banner — not the contradictory empty-state text', async () => {
    (AdminService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (AdminService.listRoles as jest.Mock).mockRejectedValue(
      new Error('Unzureichende Berechtigungen für diese Aktion'),
    );

    render(
      <RoleAssignmentDialog
        userId={42}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );

    expect(
      await screen.findByText('Unzureichende Berechtigungen für diese Aktion'),
    ).toBeInTheDocument();

    // The misleading "no roles" / "all roles assigned" fallback text must
    // NOT appear alongside the error — that contradicted the user table,
    // which (per TF-621) already showed the user's real role correctly.
    expect(screen.queryByText('admin.roleAssignment.noRoles')).toBeNull();
    expect(screen.queryByText('admin.roleAssignment.allRolesAssigned')).toBeNull();
    expect(screen.queryByText('admin.roleAssignment.currentRoles')).toBeNull();
    expect(screen.queryByText('admin.roleAssignment.availableRoles')).toBeNull();
  });

  it('TF-621: getUser failing alongside listRoles also suppresses the empty-state text', async () => {
    (AdminService.getUser as jest.Mock).mockRejectedValue(new Error('boom'));
    (AdminService.listRoles as jest.Mock).mockResolvedValue(mockRoles);

    render(
      <RoleAssignmentDialog
        userId={42}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('boom')).toBeInTheDocument();
    });
    expect(screen.queryByText('admin.roleAssignment.allRolesAssigned')).toBeNull();
  });

  it('TF-621: an assign-role failure shows the error but keeps the role lists visible', async () => {
    (AdminService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (AdminService.listRoles as jest.Mock).mockResolvedValue(mockRoles);
    (AdminService.assignRole as jest.Mock).mockRejectedValue(
      new Error('Rolle bereits zugewiesen'),
    );

    render(
      <RoleAssignmentDialog
        userId={42}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );

    const assignButton = await screen.findByText('admin.roleAssignment.btnAssign');
    fireEvent.click(assignButton);

    expect(await screen.findByText('Rolle bereits zugewiesen')).toBeInTheDocument();

    // Unlike an initial-load failure, an action failure must NOT hide the
    // already-loaded role lists — the admin still needs to see current
    // state (and retry) without closing and reopening the dialog.
    expect(screen.getByText('admin.roleAssignment.currentRoles')).toBeInTheDocument();
    expect(screen.getByText('admin.roleAssignment.availableRoles')).toBeInTheDocument();
    expect(screen.getByText('Dozent')).toBeInTheDocument();
    expect(screen.getByText('Assistant')).toBeInTheDocument();
  });

  it('TF-621: a remove-role failure shows the error but keeps the role lists visible', async () => {
    const twoRoleUser = { ...mockUser, roles: [mockRoles[0], mockRoles[1]] };
    (AdminService.getUser as jest.Mock).mockResolvedValue(twoRoleUser);
    (AdminService.listRoles as jest.Mock).mockResolvedValue(mockRoles);
    (AdminService.removeRole as jest.Mock).mockRejectedValue(
      new Error('Entfernen fehlgeschlagen'),
    );

    render(
      <RoleAssignmentDialog
        userId={42}
        isOpen={true}
        onClose={jest.fn()}
        onSuccess={jest.fn()}
      />,
    );

    const removeButtons = await screen.findAllByText('admin.roleAssignment.btnRemove');
    fireEvent.click(removeButtons[0]);

    expect(await screen.findByText('Entfernen fehlgeschlagen')).toBeInTheDocument();

    expect(screen.getByText('admin.roleAssignment.currentRoles')).toBeInTheDocument();
    expect(screen.getByText('admin.roleAssignment.availableRoles')).toBeInTheDocument();
    expect(screen.getByText('Dozent')).toBeInTheDocument();
  });
});
