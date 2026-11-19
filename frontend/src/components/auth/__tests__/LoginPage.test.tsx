import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom';
import { LoginPage } from '../LoginPage';

const mockLogin = jest.fn();
let mockNotice: string | null = null;
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin, notice: mockNotice }),
}));

// Echo the key, so the test pins which message is chosen.
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const LocationProbe: React.FC = () => {
  const location = useLocation();
  return <span data-testid="search">{location.search}</span>;
};

const renderAt = (url: string) =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <LoginPage />
      <LocationProbe />
    </MemoryRouter>,
  );

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNotice = null;
  });

  it('startet den Login-Flow des Backends per Klick', () => {
    renderAt('/login');
    fireEvent.click(screen.getByRole('button', { name: 'auth.login.signIn' }));
    expect(mockLogin).toHaveBeenCalledTimes(1);
    expect(mockLogin).toHaveBeenCalledWith();
  });

  it('startet die Kontoauswahl über «Mit anderem Konto anmelden»', () => {
    renderAt('/login');
    fireEvent.click(screen.getByRole('button', { name: 'auth.login.switchAccount' }));
    expect(mockLogin).toHaveBeenCalledWith({ switchAccount: true });
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

  it('zeigt ohne Hinweis keinen Sitzungs-Hinweis', () => {
    renderAt('/login');
    expect(screen.queryByTestId('login-notice')).not.toBeInTheDocument();
  });

  it.each(['session_expired', 'session_unavailable', 'logout_failed'])(
    'zeigt den Sitzungs-Hinweis %s',
    (notice) => {
      mockNotice = notice;
      renderAt('/login');
      expect(screen.getByTestId('login-notice')).toHaveTextContent(`auth.loginNotice.${notice}`);
    },
  );

  it('zeigt bei einem Backend-Fehlercode nur diesen und nicht zusätzlich den Sitzungs-Hinweis', () => {
    mockNotice = 'session_expired';
    renderAt('/login?error=login_failed');
    expect(screen.getByRole('alert')).toHaveTextContent('auth.loginError.login_failed');
    expect(screen.queryByTestId('login-notice')).not.toBeInTheDocument();
  });

  it('fällt bei einem unbekannten Code auf den allgemeinen Text zurück', () => {
    renderAt('/login?error=<script>alert(1)</script>');
    expect(screen.getByRole('alert')).toHaveTextContent('auth.loginError.login_failed');
  });

  // EXAMCRAFT-139: ein Reload darf die Meldung nicht wiederholen.
  it('entfernt den error-Parameter aus der URL, zeigt die Meldung aber weiter', () => {
    renderAt('/login?error=login_expired&foo=bar');
    expect(screen.getByRole('alert')).toHaveTextContent('auth.loginError.login_expired');
    expect(screen.getByTestId('search')).toHaveTextContent('?foo=bar');
  });

  it('ersetzt die Meldung, wenn bei gemounteter Seite ein neuer Fehler kommt', () => {
    const NavButton: React.FC = () => {
      const navigate = useNavigate();
      return <button onClick={() => navigate('/login?error=idp_unavailable')}>go</button>;
    };
    render(
      <MemoryRouter initialEntries={['/login?error=login_expired']}>
        <LoginPage />
        <NavButton />
      </MemoryRouter>,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('auth.loginError.login_expired');
    fireEvent.click(screen.getByText('go'));
    expect(screen.getByRole('alert')).toHaveTextContent('auth.loginError.idp_unavailable');
  });
});
