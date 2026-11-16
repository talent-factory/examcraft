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
const mockTakePending = jest.fn();
jest.mock('../ImpersonationReasonDialog', () => ({
  takePendingImpersonation: (adminId: number) => mockTakePending(adminId),
  ImpersonationReasonDialog: ({
    isOpen,
    onSuccess,
    userId,
    initialReason,
  }: {
    isOpen: boolean;
    onSuccess: () => void;
    userId: number | null;
    initialReason?: string;
  }) =>
    isOpen ? (
      <button onClick={onSuccess}>
        trigger-impersonation-started
        <span data-testid="dialog-props">{`${userId}|${initialReason}`}</span>
      </button>
    ) : null,
}));

beforeEach(() => {
  jest.clearAllMocks();
  mockHasPermission = jest.fn().mockReturnValue(true);
  mockTakePending.mockReturnValue(null);
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

  it('reopens the dialog prefilled after the step-up round trip (EXAMCRAFT-144)', () => {
    mockTakePending.mockReturnValue({ userId: 7, reason: 'restored reason' });
    render(<UserManagementPage />);

    expect(mockTakePending).toHaveBeenCalledWith(1);
    expect(screen.getByTestId('dialog-props')).toHaveTextContent('7|restored reason');
  });

  it('keeps the dialog closed when the pending request belongs to another admin', () => {
    mockTakePending.mockReturnValue(null);
    render(<UserManagementPage />);

    expect(screen.queryByText('trigger-impersonation-started')).not.toBeInTheDocument();
  });

  it('starts a fresh dialog without the restored reason for the next target', () => {
    mockTakePending.mockReturnValue({ userId: 7, reason: 'restored reason' });
    render(<UserManagementPage />);
    expect(screen.getByTestId('dialog-props')).toHaveTextContent('7|restored reason');

    fireEvent.click(screen.getByText('trigger-impersonate'));

    expect(screen.getByTestId('dialog-props')).toHaveTextContent('7|');
    expect(screen.getByTestId('dialog-props')).not.toHaveTextContent('restored');
  });

  it('does not restore a pending request without users:impersonate', () => {
    mockHasPermission.mockReturnValue(false);
    mockTakePending.mockReturnValue({ userId: 7, reason: 'restored reason' });
    render(<UserManagementPage />);

    expect(screen.queryByText('trigger-impersonation-started')).not.toBeInTheDocument();
    expect(mockTakePending).not.toHaveBeenCalled();
  });
});
