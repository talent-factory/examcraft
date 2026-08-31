/**
 * UserManagementPage tests (TF-743).
 *
 * Focused on the two behaviors that are unique to this component and not
 * covered elsewhere: handleImpersonateUser's own RBAC re-check (defense in
 * depth alongside UserList's own gate — see UserList.test.tsx for that
 * one), and the post-impersonation-start navigation to /dashboard.
 *
 * All child dialogs/lists are replaced with minimal test doubles that just
 * expose their props via buttons, so this test only exercises
 * UserManagementPage's own orchestration logic, not each child's internals
 * (already covered by their own test files).
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UserManagementPage } from '../UserManagementPage';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

let mockHasPermission: jest.Mock;
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, is_superuser: false, roles: [] },
    hasPermission: mockHasPermission,
  }),
}));

jest.mock('../UserList', () => ({
  UserList: ({ onImpersonateUser }: { onImpersonateUser: (id: number) => void }) => (
    <button onClick={() => onImpersonateUser(7)}>trigger-impersonate</button>
  ),
}));
jest.mock('../UserEditDialog', () => ({ UserEditDialog: () => null }));
jest.mock('../RoleAssignmentDialog', () => ({ RoleAssignmentDialog: () => null }));
jest.mock('../OrgUnitAssignmentDialog', () => ({ OrgUnitAssignmentDialog: () => null }));
jest.mock('../ImpersonationReasonDialog', () => ({
  ImpersonationReasonDialog: ({
    isOpen,
    onSuccess,
  }: {
    isOpen: boolean;
    onSuccess: () => void;
  }) =>
    isOpen ? <button onClick={onSuccess}>trigger-impersonation-started</button> : null,
}));

beforeEach(() => {
  jest.clearAllMocks();
  mockHasPermission = jest.fn().mockReturnValue(true);
});

describe('UserManagementPage — impersonation orchestration (TF-743)', () => {
  it('opens the impersonation dialog when the user has users:impersonate', () => {
    render(<UserManagementPage />);

    fireEvent.click(screen.getByText('trigger-impersonate'));

    expect(mockHasPermission).toHaveBeenCalledWith('users:impersonate');
    expect(screen.getByText('trigger-impersonation-started')).toBeInTheDocument();
  });

  it('does not open the impersonation dialog when the RBAC re-check fails, even if the trigger somehow fired', () => {
    // Defense in depth: UserList already hides the button in this case
    // (see UserList.test.tsx), but handleImpersonateUser must not trust
    // that alone.
    mockHasPermission.mockReturnValue(false);
    render(<UserManagementPage />);

    fireEvent.click(screen.getByText('trigger-impersonate'));

    expect(screen.queryByText('trigger-impersonation-started')).not.toBeInTheDocument();
  });

  it('navigates to /dashboard once impersonation has started', () => {
    render(<UserManagementPage />);

    fireEvent.click(screen.getByText('trigger-impersonate'));
    fireEvent.click(screen.getByText('trigger-impersonation-started'));

    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });
});
