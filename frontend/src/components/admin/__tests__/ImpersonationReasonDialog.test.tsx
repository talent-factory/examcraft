/**
 * ImpersonationReasonDialog tests (TF-743).
 *
 * Covers the logic that is unique to this component: the client-side
 * reason-length validation, loadTarget's success/failure paths, the
 * reset-on-close effect, handleSubmit's success/failure paths, and the
 * backdrop-disabled-while-saving fix.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ImpersonationReasonDialog } from '../ImpersonationReasonDialog';
import AdminService from '../../../services/AdminService';

// The global react-i18next mock (setupTests.ts) recreates `t` on every call
// to useTranslation(), which is fine for most components but breaks this
// one: loadTarget's useCallback depends on `t`, and the mount effect
// depends on loadTarget — an unstable `t` makes that effect re-fire on
// every render, forever (real react-i18next's `t` is stable across
// renders, so this never happens outside tests). Override with a stable
// `t` locally, matching the de/translation.json values this component uses.
const DE_STRINGS: Record<string, string> = {
  'admin.impersonation.dialogTitle': 'Als Nutzer anmelden',
  'admin.impersonation.dialogTargetLabel': 'Sie melden sich an als:',
  'admin.impersonation.dialogReasonLabel': 'Grund (Pflichtfeld)',
  'admin.impersonation.dialogReasonPlaceholder': 'z. B. Support-Anfrage TICKET-123 nachstellen',
  'admin.impersonation.dialogPasswordLabel': 'Ihr Passwort (Bestätigung)',
  'admin.impersonation.dialogPasswordPlaceholder': 'Ihr aktuelles Passwort',
  'admin.impersonation.dialogConfirm': 'Anmelden',
  'admin.impersonation.dialogStarting': 'Wird gestartet...',
  'admin.impersonation.dialogCancel': 'Abbrechen',
  'admin.impersonation.dialogLoadFailed': 'Benutzer konnte nicht geladen werden',
  'admin.impersonation.dialogError': 'Anmeldung als Nutzer fehlgeschlagen',
  'admin.impersonation.reasonTooShort': 'Bitte geben Sie mindestens {{min}} Zeichen als Grund an',
  'admin.impersonation.passwordRequired': 'Bitte bestätigen Sie Ihr Passwort',
};
const mockStableT = (key: string, params?: Record<string, unknown>) => {
  let value = DE_STRINGS[key] ?? key;
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      value = value.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    });
  }
  return value;
};
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: mockStableT }),
}));

jest.mock('../../../services/AdminService', () => ({
  __esModule: true,
  default: {
    getUser: jest.fn(),
    impersonateUser: jest.fn(),
  },
}));

const mockStartImpersonation = jest.fn();
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ startImpersonation: mockStartImpersonation }),
}));

const mockedAdminService = AdminService as jest.Mocked<typeof AdminService>;

const targetUser = {
  id: 7,
  email: 'max@example.com',
  first_name: 'Max',
  last_name: 'Muster',
  institution_id: 1,
  institution_name: 'Test Institution',
  roles: [],
  org_units: [],
  status: 'active',
  is_superuser: false,
  created_at: '2026-01-01T00:00:00Z',
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedAdminService.getUser.mockResolvedValue(targetUser as any);
  mockedAdminService.impersonateUser.mockResolvedValue({
    access_token: 'target-access-token',
    token_type: 'bearer',
    expires_in: 1800,
    impersonation_session_id: 1,
    target_user_id: 7,
    target_user_email: 'max@example.com',
  } as any);
  mockStartImpersonation.mockResolvedValue(undefined);
});

const renderDialog = (overrides: Partial<React.ComponentProps<typeof ImpersonationReasonDialog>> = {}) => {
  const onClose = jest.fn();
  const onSuccess = jest.fn();
  const utils = render(
    <ImpersonationReasonDialog
      userId={7}
      isOpen={true}
      onClose={onClose}
      onSuccess={onSuccess}
      {...overrides}
    />,
  );
  return { ...utils, onClose, onSuccess };
};

describe('ImpersonationReasonDialog', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <ImpersonationReasonDialog userId={7} isOpen={false} onClose={jest.fn()} onSuccess={jest.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('loads and displays the target user when opened', async () => {
    renderDialog();

    expect(mockedAdminService.getUser).toHaveBeenCalledWith(7);
    await waitFor(() => {
      expect(screen.getByText(/Max Muster/)).toBeInTheDocument();
    });
    expect(screen.getByText(/max@example\.com/)).toBeInTheDocument();
  });

  it('shows an error and no target when loading the target fails', async () => {
    mockedAdminService.getUser.mockRejectedValueOnce(new Error('user not found'));

    renderDialog();

    await waitFor(() => {
      expect(screen.getByText('user not found')).toBeInTheDocument();
    });
    expect(screen.queryByText(/Max Muster/)).not.toBeInTheDocument();
  });

  it('rejects a reason shorter than the minimum without calling the API', async () => {
    renderDialog();
    await screen.findByText(/Max Muster/);

    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'ab' } });
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));

    expect(await screen.findByText(/mindestens 3 Zeichen/)).toBeInTheDocument();
    expect(mockedAdminService.impersonateUser).not.toHaveBeenCalled();
    expect(mockStartImpersonation).not.toHaveBeenCalled();
  });

  it('rejects submit without an admin password, without calling the API', async () => {
    renderDialog();
    await screen.findByText(/Max Muster/);

    fireEvent.change(screen.getByLabelText(/Grund/), {
      target: { value: 'reproduce support ticket TICKET-123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));

    expect(await screen.findByText('Bitte bestätigen Sie Ihr Passwort')).toBeInTheDocument();
    expect(mockedAdminService.impersonateUser).not.toHaveBeenCalled();
    expect(mockStartImpersonation).not.toHaveBeenCalled();
  });

  it('starts impersonation and closes on a valid reason and password', async () => {
    const { onClose, onSuccess } = renderDialog();
    await screen.findByText(/Max Muster/);

    fireEvent.change(screen.getByLabelText(/Grund/), {
      target: { value: 'reproduce support ticket TICKET-123' },
    });
    fireEvent.change(screen.getByLabelText(/Ihr Passwort/), {
      target: { value: 'MyOwnPassword1!' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(mockedAdminService.impersonateUser).toHaveBeenCalledWith(
      7,
      'reproduce support ticket TICKET-123',
      'MyOwnPassword1!',
    );
    expect(mockStartImpersonation).toHaveBeenCalledWith({
      accessToken: 'target-access-token',
      expiresIn: 1800,
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('shows an error and stays open when AdminService.impersonateUser fails', async () => {
    mockedAdminService.impersonateUser.mockRejectedValueOnce(new Error('quota exceeded'));
    const { onClose, onSuccess } = renderDialog();
    await screen.findByText(/Max Muster/);

    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'valid reason text' } });
    fireEvent.change(screen.getByLabelText(/Ihr Passwort/), { target: { value: 'MyOwnPassword1!' } });
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));

    expect(await screen.findByText('quota exceeded')).toBeInTheDocument();
    expect(mockStartImpersonation).not.toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    // TF-758 review fix: a failed attempt (e.g. wrong password) must not
    // leave the password sitting in the input.
    expect((screen.getByLabelText(/Ihr Passwort/) as HTMLInputElement).value).toBe('');
  });

  it('shows an error and stays open when startImpersonation fails after the backend already created the session', async () => {
    mockStartImpersonation.mockRejectedValueOnce(new Error('storage restricted'));
    const { onClose, onSuccess } = renderDialog();
    await screen.findByText(/Max Muster/);

    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'valid reason text' } });
    fireEvent.change(screen.getByLabelText(/Ihr Passwort/), { target: { value: 'MyOwnPassword1!' } });
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));

    expect(await screen.findByText('storage restricted')).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    expect((screen.getByLabelText(/Ihr Passwort/) as HTMLInputElement).value).toBe('');
  });

  it('resets target, reason, and error when closed, so reopening for a different user starts clean', async () => {
    mockedAdminService.getUser.mockRejectedValueOnce(new Error('boom'));
    const { rerender } = renderDialog();
    await screen.findByText('boom');
    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'some leftover text' } });
    fireEvent.change(screen.getByLabelText(/Ihr Passwort/), { target: { value: 'leftover-pw' } });

    rerender(
      <ImpersonationReasonDialog userId={7} isOpen={false} onClose={jest.fn()} onSuccess={jest.fn()} />,
    );

    mockedAdminService.getUser.mockResolvedValueOnce({ ...targetUser, id: 8, first_name: 'Erika' } as any);
    rerender(
      <ImpersonationReasonDialog userId={8} isOpen={true} onClose={jest.fn()} onSuccess={jest.fn()} />,
    );

    await screen.findByText(/Erika/);
    expect(screen.queryByText('boom')).not.toBeInTheDocument();
    expect((screen.getByLabelText(/Grund/) as HTMLTextAreaElement).value).toBe('');
    expect((screen.getByLabelText(/Ihr Passwort/) as HTMLInputElement).value).toBe('');
  });

  it('does not close on a backdrop click while saving, but does once saving finishes', async () => {
    let resolveImpersonate: (value: unknown) => void = () => {};
    mockedAdminService.impersonateUser.mockReturnValue(
      new Promise((resolve) => {
        resolveImpersonate = resolve;
      }) as any,
    );

    const { onClose } = renderDialog();
    await screen.findByText(/Max Muster/);

    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'valid reason text' } });
    fireEvent.change(screen.getByLabelText(/Ihr Passwort/), { target: { value: 'MyOwnPassword1!' } });
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));

    // Still saving: clicking the backdrop must not close the dialog out
    // from under an in-flight request.
    fireEvent.click(screen.getByTestId('impersonation-dialog-backdrop'));
    expect(onClose).not.toHaveBeenCalled();

    resolveImpersonate({
      access_token: 'target-access-token',
      token_type: 'bearer',
      expires_in: 1800,
      impersonation_session_id: 1,
      target_user_id: 7,
      target_user_email: 'max@example.com',
    });

    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('closes on a backdrop click when not saving', async () => {
    const { onClose } = renderDialog();
    await screen.findByText(/Max Muster/);

    fireEvent.click(screen.getByTestId('impersonation-dialog-backdrop'));

    expect(onClose).toHaveBeenCalled();
  });
});
