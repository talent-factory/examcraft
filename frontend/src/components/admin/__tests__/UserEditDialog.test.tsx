/**
 * UserEditDialog tests.
 *
 * TF-772 PR 3: `loadUser`, `loadInstitutions` and `handleSubmit`'s catch
 * blocks migrated to `translateError`. This component had no test file at
 * all, so the migration went live with zero coverage of any of its three
 * error paths — these tests pin that behaviour.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { UserEditDialog } from '../UserEditDialog';
import AdminService from '../../../services/AdminService';
import { AppError } from '../../../errors';

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: {
    getUser: jest.fn(),
    updateUser: jest.fn(),
    listInstitutions: jest.fn(),
  },
}));

const mockCurrentUser = { id: 1, is_superuser: false };
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockCurrentUser }),
}));

jest.mock('react-i18next', () => {
  // A mock that echoes every key would send every AppError down the fallback
  // branch and make the translated-text assertion below silently vacuous —
  // resolve the real errors.* block, same as the sibling admin dialog tests.
  //
  // `t` must be hoisted OUTSIDE useTranslation() and stay referentially
  // stable across calls, exactly like the real i18next's `t`: this
  // component's loadUser/loadInstitutions are useCallback([...,  t]), so an
  // unstable mock `t` reference re-triggers their effects on every render —
  // an infinite load->render->reload loop that never lets state settle.
  const de = require('../../../locales/de/translation.json');
  const t = (key: string) =>
    key.startsWith('errors.') ? (de.errors[key.slice('errors.'.length)] ?? key) : key;
  return {
    useTranslation: () => ({ t }),
  };
});

const mockUser = {
  id: 7,
  email: 'u@x',
  first_name: 'Max',
  last_name: 'Muster',
  institution_id: 1,
  institution_name: 'BWZ Lyss',
  roles: [],
  status: 'active',
  is_superuser: false,
  created_at: '2026-01-01',
};

describe('UserEditDialog', () => {
  it('shows the translated message when getUser rejects with a specific code', async () => {
    (AdminService.getUser as jest.Mock).mockRejectedValue(
      new AppError('admin_user_load_failed', 'User could not be loaded', 404),
    );

    render(<UserEditDialog userId={7} isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />);

    expect(
      await screen.findByText('Benutzer konnte nicht geladen werden'),
    ).toBeInTheDocument();
  });

  it('shows the fallback banner when getUser rejects without a specific code', async () => {
    (AdminService.getUser as jest.Mock).mockRejectedValue(new Error('network blip'));

    render(<UserEditDialog userId={7} isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('admin.userEditDialog.failedLoad')).toBeInTheDocument();
    });
  });

  it('shows the translated message when updateUser rejects with a specific code', async () => {
    (AdminService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (AdminService.updateUser as jest.Mock).mockRejectedValue(
      new AppError('admin_user_update_failed', 'User could not be updated', 500),
    );

    render(<UserEditDialog userId={7} isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />);

    const firstName = await screen.findByLabelText('admin.userEditDialog.firstNameLabel');
    fireEvent.change(firstName, { target: { value: 'Moritz' } });
    fireEvent.click(screen.getByText('admin.userEditDialog.saveChanges'));

    expect(
      await screen.findByText('Benutzer konnte nicht aktualisiert werden'),
    ).toBeInTheDocument();
  });

  it('disables the transfer button and shows the load-failed note when loadInstitutions rejects for a superuser', async () => {
    // `translateError`'s return value here (`msg`) only ever drives the
    // `institutionsError !== null` gate — the JSX renders a static
    // `admin.institutionTransfer.institutionsLoadFailed` string regardless of
    // which branch produced it (see the component). So the observable
    // contract this test can pin is: the catch block ran, the note appears,
    // and the transfer button is disabled — not which translateError branch
    // fired.
    mockCurrentUser.is_superuser = true;
    (AdminService.getUser as jest.Mock).mockResolvedValue(mockUser);
    (AdminService.listInstitutions as jest.Mock).mockRejectedValue(new Error('network blip'));

    render(<UserEditDialog userId={7} isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />);

    await waitFor(() => {
      expect(
        screen.getByText('admin.institutionTransfer.institutionsLoadFailed'),
      ).toBeInTheDocument();
    });
    expect(screen.getByText('admin.institutionTransfer.button')).toBeDisabled();

    mockCurrentUser.is_superuser = false;
  });
});
