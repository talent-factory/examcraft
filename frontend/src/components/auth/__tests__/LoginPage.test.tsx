import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../LoginPage';

const mockLogin = jest.fn();
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

// Echo the key, so the test pins which message is chosen.
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const renderAt = (url: string) =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <LoginPage />
    </MemoryRouter>,
  );

describe('LoginPage', () => {
  beforeEach(() => jest.clearAllMocks());

  it('startet den Login-Flow des Backends per Klick', () => {
    renderAt('/login');
    fireEvent.click(screen.getByRole('button', { name: 'auth.login.signIn' }));
    expect(mockLogin).toHaveBeenCalledTimes(1);
  });

  it('zeigt ohne error-Parameter keine Fehlermeldung', () => {
    renderAt('/login');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it.each([
    'login_failed',
    'login_expired',
    'login_cancelled',
    'idp_unavailable',
    'email_conflict',
    'account_not_migrated',
    'user_limit',
    'claims_missing',
    'account_inactive',
    'reauth_failed',
  ])('übersetzt den Backend-Fehlercode %s', (code) => {
    renderAt(`/login?error=${code}`);
    expect(screen.getByRole('alert')).toHaveTextContent(`auth.loginError.${code}`);
  });

  it('fällt bei einem unbekannten Code auf den allgemeinen Text zurück', () => {
    renderAt('/login?error=<script>alert(1)</script>');
    expect(screen.getByRole('alert')).toHaveTextContent('auth.loginError.login_failed');
  });
});
