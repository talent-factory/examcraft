/**
 * OrgUnitAssignmentDialog tests (TF-602).
 *
 * Mirrors what OrgUnitEditor.test.tsx / AdminOrgUnits.test.tsx cover for the
 * hierarchy editor, but for member assignment: loading a user's current
 * memberships + all org units, assigning (with/without a role), removing,
 * and surfacing load/assign/remove errors.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { OrgUnitAssignmentDialog } from '../OrgUnitAssignmentDialog';
import AdminService, { UserDetailResponse } from '../../../services/AdminService';
import { AppError } from '../../../errors';
import { OrgUnitsService } from '../../../services/orgUnitsService';
import { OrgUnitOut } from '../../../types/orgUnit';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: { getUser: jest.fn() },
}));

jest.mock('../../../services/orgUnitsService', () => ({
  OrgUnitsService: { list: jest.fn(), addMember: jest.fn(), removeMember: jest.fn() },
}));

const mockUseAuth = jest.fn(() => ({ user: { institution_id: 1 } }));
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

const mockedAdminService = AdminService as jest.Mocked<typeof AdminService>;
const mockedOrgUnitsService = OrgUnitsService as jest.Mocked<typeof OrgUnitsService>;

function makeUnit(overrides: Partial<OrgUnitOut> = {}): OrgUnitOut {
  return {
    id: 1,
    parent_org_unit_id: null,
    unit_type: 'abteilung',
    name: 'Informatik',
    descendant_count: 0,
    role_id: null,
    role_name: null,
    created_at: '2026-08-07T00:00:00Z',
    updated_at: '2026-08-07T00:00:00Z',
    ...overrides,
  };
}

function makeUser(overrides: Partial<UserDetailResponse> = {}): UserDetailResponse {
  return {
    id: 7,
    email: 'member@example.com',
    first_name: 'Max',
    last_name: 'Muster',
    institution_id: 1,
    institution_name: 'Test-Institution',
    roles: [],
    org_units: [],
    status: 'active',
    is_superuser: false,
    created_at: '2026-08-07T00:00:00Z',
    ...overrides,
  };
}

beforeEach(() => jest.clearAllMocks());

describe('OrgUnitAssignmentDialog', () => {
  it('loads and shows current and available org units, with parent name resolved', async () => {
    mockedAdminService.getUser.mockResolvedValue(
      makeUser({
        org_units: [
          { org_unit_id: 1, name: 'Informatik', unit_type: 'abteilung', parent_org_unit_id: null, role: null },
        ],
      }),
    );
    mockedOrgUnitsService.list.mockResolvedValue({
      items: [
        makeUnit({ id: 1, name: 'Informatik' }),
        makeUnit({ id: 2, name: 'Backend-Team', unit_type: 'team', parent_org_unit_id: 1 }),
      ],
    });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    expect(await screen.findByTestId('ouad-current-1')).toHaveTextContent('Informatik');
    expect(screen.getByTestId('ouad-available-2')).toHaveTextContent('Backend-Team (Informatik)');
  });

  // TF-637: Granted Role is a separate row from the Membership Label
  // (`membership.role`, free text like "Leiter") -- Variant B from the
  // prototype, https://claude.ai/code/artifact/d4df5f67-49de-49d4-9d19-b2abe2e0213a
  it('shows the granted role of a current membership on its own row, separate from the membership label', async () => {
    mockedAdminService.getUser.mockResolvedValue(
      makeUser({
        org_units: [
          {
            org_unit_id: 2,
            name: 'Backend-Team',
            unit_type: 'team',
            parent_org_unit_id: null,
            role: 'Leiter',
          },
        ],
      }),
    );
    mockedOrgUnitsService.list.mockResolvedValue({
      items: [makeUnit({ id: 2, name: 'Backend-Team', role_id: 5, role_name: 'Backend-Grader' })],
    });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    const row = await screen.findByTestId('ouad-current-2');
    expect(row).toHaveTextContent('Backend-Grader');
    expect(row).toHaveTextContent('Leiter');
  });

  it('shows the granted role of an available org unit', async () => {
    mockedAdminService.getUser.mockResolvedValue(makeUser());
    mockedOrgUnitsService.list.mockResolvedValue({
      items: [makeUnit({ id: 2, name: 'Backend-Team', role_id: 5, role_name: 'Backend-Grader' })],
    });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    expect(await screen.findByTestId('ouad-available-2')).toHaveTextContent('Backend-Grader');
  });

  it('shows no "verleiht:" row when the org unit has no granted role', async () => {
    mockedAdminService.getUser.mockResolvedValue(makeUser());
    mockedOrgUnitsService.list.mockResolvedValue({
      items: [makeUnit({ id: 2, name: 'Backend-Team' })],
    });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    const row = await screen.findByTestId('ouad-available-2');
    expect(row).not.toHaveTextContent('verleiht');
  });

  it('assigns the selected org unit with the entered role', async () => {
    mockedAdminService.getUser.mockResolvedValue(makeUser());
    mockedOrgUnitsService.list.mockResolvedValue({ items: [makeUnit({ id: 2, name: 'Backend-Team' })] });
    mockedOrgUnitsService.addMember.mockResolvedValue({ user_id: 7, org_unit_id: 2 });
    const onSuccess = jest.fn();

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={onSuccess} />);

    await screen.findByTestId('ouad-available-2');
    fireEvent.change(screen.getByTestId('ouad-role-input-2'), { target: { value: 'Leiter' } });
    fireEvent.click(screen.getByTestId('ouad-btn-assign-2'));

    await waitFor(() => expect(mockedOrgUnitsService.addMember).toHaveBeenCalledWith(2, 7, 'Leiter'));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('ouad-btn-assign-2')).not.toBeDisabled());
  });

  it('assigns without a role when the role input is left blank', async () => {
    mockedAdminService.getUser.mockResolvedValue(makeUser());
    mockedOrgUnitsService.list.mockResolvedValue({ items: [makeUnit({ id: 2, name: 'Backend-Team' })] });
    mockedOrgUnitsService.addMember.mockResolvedValue({ user_id: 7, org_unit_id: 2 });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    fireEvent.click(await screen.findByTestId('ouad-btn-assign-2'));

    await waitFor(() => expect(mockedOrgUnitsService.addMember).toHaveBeenCalledWith(2, 7, undefined));
    await waitFor(() => expect(screen.getByTestId('ouad-btn-assign-2')).not.toBeDisabled());
  });

  it('removes a current membership', async () => {
    mockedAdminService.getUser.mockResolvedValue(
      makeUser({
        org_units: [
          { org_unit_id: 1, name: 'Informatik', unit_type: 'abteilung', parent_org_unit_id: null, role: null },
        ],
      }),
    );
    mockedOrgUnitsService.list.mockResolvedValue({ items: [makeUnit({ id: 1, name: 'Informatik' })] });
    mockedOrgUnitsService.removeMember.mockResolvedValue(undefined);
    const onSuccess = jest.fn();

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={onSuccess} />);

    fireEvent.click(await screen.findByTestId('ouad-btn-remove-1'));

    await waitFor(() => expect(mockedOrgUnitsService.removeMember).toHaveBeenCalledWith(1, 7));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('ouad-btn-remove-1')).not.toBeDisabled());
  });

  it('shows an error message when loading fails', async () => {
    mockedAdminService.getUser.mockRejectedValue(
      new AppError('admin_user_not_found', 'User not found', 404),
    );
    mockedOrgUnitsService.list.mockResolvedValue({ items: [] });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    expect(await screen.findByTestId('ouad-error')).toHaveTextContent(
      'Benutzer nicht gefunden',
    );
  });

  it('zeigt beim OrgUnits-Zweig desselben catch den generischen Fallback', async () => {
    // `loadData` awaits AdminService.getUser and OrgUnitsService.list under
    // one catch. Converting it was not optional — an AppError without
    // `detail` would otherwise have rendered its bare code — but
    // OrgUnitsService still throws plain Errors, so its specific text is
    // replaced by the generic fallback here until that service itself is
    // migrated (PR 4 territory). The two tests below pin the same behaviour
    // for the other two catches (assign/remove), migrated in the TF-772 PR 3
    // review-fixes round for consistency within this one dialog.
    mockedAdminService.getUser.mockResolvedValue(makeUser());
    mockedOrgUnitsService.list.mockRejectedValue(new Error('OrgUnits-Dienst nicht erreichbar'));

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    const banner = await screen.findByTestId('ouad-error');
    expect(banner).toHaveTextContent('Daten konnten nicht geladen werden');
    expect(banner).not.toHaveTextContent('OrgUnits-Dienst nicht erreichbar');
  });

  it('shows the translated fallback (not the raw message) and re-enables the button when assigning fails', async () => {
    mockedAdminService.getUser.mockResolvedValue(makeUser());
    mockedOrgUnitsService.list.mockResolvedValue({ items: [makeUnit({ id: 2, name: 'Backend-Team' })] });
    mockedOrgUnitsService.addMember.mockRejectedValue(new Error('Bereits zugeordnet'));
    const onSuccess = jest.fn();

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={onSuccess} />);

    fireEvent.click(await screen.findByTestId('ouad-btn-assign-2'));

    const banner = await screen.findByTestId('ouad-error');
    expect(banner).toHaveTextContent('Zuweisung fehlgeschlagen');
    expect(banner).not.toHaveTextContent('Bereits zugeordnet');
    expect(onSuccess).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByTestId('ouad-btn-assign-2')).not.toBeDisabled());
  });

  it('shows the translated fallback (not the raw message) and re-enables the button when removing fails', async () => {
    mockedAdminService.getUser.mockResolvedValue(
      makeUser({
        org_units: [
          { org_unit_id: 1, name: 'Informatik', unit_type: 'abteilung', parent_org_unit_id: null, role: null },
        ],
      }),
    );
    mockedOrgUnitsService.list.mockResolvedValue({ items: [makeUnit({ id: 1, name: 'Informatik' })] });
    mockedOrgUnitsService.removeMember.mockRejectedValue(new Error('OrgUnit nicht gefunden'));
    const onSuccess = jest.fn();

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={onSuccess} />);

    fireEvent.click(await screen.findByTestId('ouad-btn-remove-1'));

    const banner = await screen.findByTestId('ouad-error');
    expect(banner).toHaveTextContent('Entfernen fehlgeschlagen');
    expect(banner).not.toHaveTextContent('OrgUnit nicht gefunden');
    expect(onSuccess).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByTestId('ouad-btn-remove-1')).not.toBeDisabled());
  });

  it('shows the empty-state copy when the user has no memberships', async () => {
    mockedAdminService.getUser.mockResolvedValue(makeUser({ org_units: [] }));
    mockedOrgUnitsService.list.mockResolvedValue({ items: [] });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    expect(await screen.findByText('Keiner Organisationseinheit zugewiesen')).toBeInTheDocument();
  });

  it('shows a cross-institution notice instead of assignable org units when the managed user belongs to a different institution', async () => {
    mockUseAuth.mockReturnValue({ user: { institution_id: 1 } });
    mockedAdminService.getUser.mockResolvedValue(
      makeUser({
        institution_id: 2,
        org_units: [
          { org_unit_id: 1, name: 'Informatik', unit_type: 'abteilung', parent_org_unit_id: null, role: null },
        ],
      }),
    );
    mockedOrgUnitsService.list.mockResolvedValue({
      items: [makeUnit({ id: 1, name: 'Informatik' }), makeUnit({ id: 2, name: 'Backend-Team' })],
    });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    expect(await screen.findByTestId('ouad-cross-institution-notice')).toBeInTheDocument();
    // Current memberships still render as usual.
    expect(screen.getByTestId('ouad-current-1')).toHaveTextContent('Informatik');
    // But no assignable "available" rows are shown, even though unassigned units exist.
    expect(screen.queryByTestId('ouad-available-1')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ouad-available-2')).not.toBeInTheDocument();
  });

  it('hides the remove button on current memberships when the managed user belongs to a different institution', async () => {
    mockUseAuth.mockReturnValue({ user: { institution_id: 1 } });
    mockedAdminService.getUser.mockResolvedValue(
      makeUser({
        institution_id: 2,
        org_units: [
          { org_unit_id: 1, name: 'Informatik', unit_type: 'abteilung', parent_org_unit_id: null, role: null },
        ],
      }),
    );
    mockedOrgUnitsService.list.mockResolvedValue({ items: [makeUnit({ id: 1, name: 'Informatik' })] });

    render(<OrgUnitAssignmentDialog userId={7} isOpen onClose={jest.fn()} onSuccess={jest.fn()} />);

    // Current membership still renders with its name...
    expect(await screen.findByTestId('ouad-current-1')).toHaveTextContent('Informatik');
    // ...but without a functional remove action, since the backend lookup is scoped to
    // the caller's own institution and would 404 for a cross-institution membership.
    expect(screen.queryByTestId('ouad-btn-remove-1')).not.toBeInTheDocument();
  });
});
