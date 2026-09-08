/**
 * UserList tests (TF-602, TF-743, TF-801).
 *
 * Scoped to:
 *  - The actions kebab menu (TF-801): all per-row actions (Bearbeiten,
 *    Rollen, Org-Units, Deaktivieren/Aktivieren, Impersonieren) are
 *    collapsed behind a single "⋮" trigger per row
 *    (`ul-actions-menu-trigger-{id}`) that opens a dropdown; the
 *    individual action testids below remain stable, but are now only
 *    present in the DOM while that row's menu is open.
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
 *
 * Interaction note: state-changing clicks use `fireEvent.click` (not the
 * raw DOM `.click()` method) — Testing Library wraps `fireEvent` in `act()`,
 * which avoids the "update ... was not wrapped in act(...)" console warning
 * and matches the library's recommended API for driving React state updates
 * from a test.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UserList } from '../UserList';
import AdminService from '../../../services/AdminService';
import { UserStatus } from '../../../types/auth';

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

/** Opens the actions kebab menu for the given row, waits for it to render, and returns the trigger. */
const openActionsMenu = async (userId: number) => {
  const trigger = await screen.findByTestId(`ul-actions-menu-trigger-${userId}`);
  fireEvent.click(trigger);
  return trigger;
};

beforeEach(() => {
  jest.clearAllMocks();
  mockCurrentUser = undefined;
  mockedAdminService.listUsers.mockResolvedValue(makeListResponse([memberRow]));
});

describe('UserList — actions kebab menu (TF-801)', () => {
  it('renders a single actions-menu trigger instead of always-visible action buttons', async () => {
    mockHasPermission.mockReturnValue(false);

    renderList();

    expect(await screen.findByTestId('ul-actions-menu-trigger-7')).toBeInTheDocument();
    expect(screen.queryByText('Bearbeiten')).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: 'Rollen' })).not.toBeInTheDocument();
  });

  it('opens the menu on trigger click and shows the edit/roles actions', async () => {
    mockHasPermission.mockReturnValue(false);

    renderList();
    await openActionsMenu(7);

    expect(await screen.findByText('Bearbeiten')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Rollen' })).toBeInTheDocument();
  });

  it('calls onEditUser and closes the menu when Bearbeiten is selected', async () => {
    mockHasPermission.mockReturnValue(false);
    const onEditUser = jest.fn();

    renderList({ onEditUser });
    await openActionsMenu(7);

    const editButton = await screen.findByText('Bearbeiten');
    fireEvent.click(editButton);

    expect(onEditUser).toHaveBeenCalledWith(7);
    expect(screen.queryByText('Bearbeiten')).not.toBeInTheDocument();
  });

  it('closes the menu when clicking outside of it', async () => {
    mockHasPermission.mockReturnValue(false);

    renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    fireEvent.mouseDown(document.body);

    expect(screen.queryByText('Bearbeiten')).not.toBeInTheDocument();
  });

  it('closes the menu on Escape', async () => {
    mockHasPermission.mockReturnValue(false);

    renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(screen.queryByText('Bearbeiten')).not.toBeInTheDocument();
  });

  it('keeps only one row menu open at a time', async () => {
    mockHasPermission.mockReturnValue(false);
    mockedAdminService.listUsers.mockResolvedValue(
      makeListResponse([
        memberRow,
        { ...memberRow, id: 8, email: 'other@example.com', first_name: 'Erika', last_name: 'Beispiel' },
      ]),
    );

    renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    await openActionsMenu(8);

    expect(screen.getAllByText('Bearbeiten')).toHaveLength(1);
  });

  it('closes the menu when the already-open trigger is clicked again', async () => {
    mockHasPermission.mockReturnValue(false);

    renderList();
    const trigger = await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    fireEvent.click(trigger);

    expect(screen.queryByText('Bearbeiten')).not.toBeInTheDocument();
  });

  it('exposes aria-haspopup/aria-expanded/aria-controls on the trigger, toggling aria-expanded with the menu', async () => {
    mockHasPermission.mockReturnValue(false);

    renderList();
    const trigger = await screen.findByTestId('ul-actions-menu-trigger-7');
    expect(trigger).toHaveAttribute('aria-haspopup', 'menu');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger).not.toHaveAttribute('aria-controls');

    fireEvent.click(trigger);
    await screen.findByText('Bearbeiten');

    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(trigger).toHaveAttribute('aria-controls', 'ul-actions-menu-7');
    expect(screen.getByRole('menu')).toHaveAttribute('id', 'ul-actions-menu-7');
    expect(screen.getByRole('menu')).toHaveAccessibleName();

    fireEvent.click(trigger);

    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('calls AdminService.updateUserStatus and closes the menu when the status-toggle action is selected', async () => {
    mockHasPermission.mockReturnValue(false);
    mockedAdminService.updateUserStatus.mockResolvedValue(undefined);

    renderList();
    await openActionsMenu(7);

    const toggleButton = await screen.findByTestId('ul-btn-toggle-status-7');
    expect(toggleButton).toHaveTextContent('Deaktivieren');

    fireEvent.click(toggleButton);

    // Menu closes immediately (before the async status update resolves),
    // matching every other menu-item action.
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(mockedAdminService.updateUserStatus).toHaveBeenCalledWith(7, UserStatus.INACTIVE);
    });
    // Wait out the reload triggered by handleStatusToggle so its state
    // updates settle before the test (and its module mocks) tear down.
    await waitFor(() => expect(mockedAdminService.listUsers).toHaveBeenCalledTimes(2));
  });

  it('removes its document/window listeners when unmounted while the menu is open', async () => {
    mockHasPermission.mockReturnValue(false);
    const addSpy = jest.spyOn(document, 'addEventListener');
    const removeSpy = jest.spyOn(document, 'removeEventListener');

    const { unmount } = renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    const addedTypes = addSpy.mock.calls.map(([type]) => type);
    expect(addedTypes).toEqual(expect.arrayContaining(['mousedown', 'keydown']));

    unmount();

    const removedTypes = removeSpy.mock.calls.map(([type]) => type);
    expect(removedTypes).toEqual(expect.arrayContaining(['mousedown', 'keydown']));

    addSpy.mockRestore();
    removeSpy.mockRestore();
  });
});

describe('UserList — Org-Units button permission gate', () => {
  it('hides the Org-Units button when the user lacks manage_org_units', async () => {
    mockHasPermission.mockReturnValue(false);

    renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    expect(screen.queryByTestId('ul-btn-org-units-7')).not.toBeInTheDocument();
  });

  it('shows the Org-Units button and calls onManageOrgUnits when the user has manage_org_units', async () => {
    mockHasPermission.mockReturnValue(true);
    const onManageOrgUnits = jest.fn();

    renderList({ onManageOrgUnits });
    await openActionsMenu(7);

    const button = await screen.findByTestId('ul-btn-org-units-7');
    fireEvent.click(button);
    expect(onManageOrgUnits).toHaveBeenCalledWith(7);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });
});

describe('UserList — Impersonate button permission/scope gate (TF-743)', () => {
  it('hides the Impersonate button when the user lacks users:impersonate, even as superuser', async () => {
    mockHasPermission.mockReturnValue(false);
    mockCurrentUser = { id: 1, is_superuser: true, institution_id: 1 };

    renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });

  it('shows the Impersonate button for a SuperAdmin targeting any user and calls onImpersonateUser', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: true, institution_id: 99 }; // different institution — irrelevant for a SuperAdmin
    const onImpersonateUser = jest.fn();

    renderList({ onImpersonateUser });
    await openActionsMenu(7);

    const button = await screen.findByTestId('ul-btn-impersonate-7');
    fireEvent.click(button);
    expect(onImpersonateUser).toHaveBeenCalledWith(7);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('hides the Impersonate button for the SuperAdmin\'s own row (no self-impersonation)', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 7, is_superuser: true, institution_id: 1 };

    renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });

  it('shows the Impersonate button for an institution admin targeting a non-admin user of the same institution', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: false, institution_id: 1 };

    renderList();
    await openActionsMenu(7);

    expect(await screen.findByTestId('ul-btn-impersonate-7')).toBeInTheDocument();
  });

  it('hides the Impersonate button for an institution admin targeting a user of a different institution', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: false, institution_id: 2 };

    renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });

  it('hides the Impersonate button for an institution admin targeting a user with the admin role', async () => {
    mockHasPermission.mockReturnValue(true);
    mockCurrentUser = { id: 1, is_superuser: false, institution_id: 1 };
    mockedAdminService.listUsers.mockResolvedValue(
      makeListResponse([{ ...memberRow, roles: ['admin'] }]),
    );

    renderList();
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

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
    await openActionsMenu(7);
    await screen.findByText('Bearbeiten');

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
    await openActionsMenu(7);

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
    expect(screen.queryByTestId('ul-actions-menu-trigger-7')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ul-btn-impersonate-7')).not.toBeInTheDocument();
  });
});
