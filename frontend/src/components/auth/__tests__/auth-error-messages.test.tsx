import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { AppError } from '../../../errors';
import { LoginForm } from '../LoginForm';
import { PasswordResetConfirm } from '../PasswordResetConfirm';
import { PasswordResetRequest } from '../PasswordResetRequest';
import ResendVerificationButton from '../ResendVerificationButton';

/**
 * The three auth surfaces outside `AuthContext` that put a service failure on
 * screen themselves (TF-772 PR 3). None of them had error-path coverage.
 *
 * `ResendVerificationButton` is the odd one out: it fetches
 * `/api/auth/resend-verification` inline instead of going through
 * `AuthService`, which is why the i18n guard never reported its English
 * literal — the `literal-error` rule only scans `services/` and `api/`. It is
 * covered here for the same reason it was migrated: the endpoint is an auth
 * endpoint and answers with `auth_*` codes.
 */

jest.mock('../../../services/AuthService', () => ({
  __esModule: true,
  default: {
    requestPasswordReset: jest.fn(),
    confirmPasswordReset: jest.fn(),
  },
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
  useSearchParams: () => [new URLSearchParams({ token: 'reset-token' }), jest.fn()],
}));

// Only LoginForm needs this; the other three components here take no context.
// `error: null` matters: LoginForm renders `error || localError`, so a context
// error would mask the local one this file is about.
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    login: jest.fn(),
    error: null,
    isLoading: false,
    clearError: jest.fn(),
  }),
}));

// eslint-disable-next-line import/first
import AuthService from '../../../services/AuthService';

const mockAuthService = AuthService as jest.Mocked<typeof AuthService>;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('PasswordResetRequest', () => {
  function submit(): void {
    render(
      <MemoryRouter>
        <PasswordResetRequest />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText(/E-Mail/i), {
      target: { value: 'user@example.ch' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Link/i }));
  }

  it('zeigt die Übersetzung des Backend-Codes', async () => {
    (mockAuthService.requestPasswordReset as jest.Mock).mockRejectedValue(
      new AppError('auth_service_unavailable', 'Service temporarily unavailable', 503),
    );

    submit();

    expect(await screen.findByText('Dienst vorübergehend nicht verfügbar')).toBeInTheDocument();
  });

  it('zeigt bei einem untypisierten Fehler den Fallback statt dessen message', async () => {
    (mockAuthService.requestPasswordReset as jest.Mock).mockRejectedValue(
      new Error('Failed to fetch'),
    );

    submit();

    expect(
      await screen.findByText('Zurücksetzen des Passworts konnte nicht angefordert werden'),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Failed to fetch/)).not.toBeInTheDocument();
  });
});

describe('PasswordResetConfirm', () => {
  function submit(): void {
    render(
      <MemoryRouter>
        <PasswordResetConfirm />
      </MemoryRouter>,
    );
    const [password, confirmation] = screen.getAllByPlaceholderText('••••••••');
    fireEvent.change(password, { target: { value: 'Sicher!2345' } });
    fireEvent.change(confirmation, { target: { value: 'Sicher!2345' } });
    fireEvent.click(screen.getByRole('button', { name: /zurücksetzen/i }));
  }

  it('zeigt die Übersetzung des Backend-Codes', async () => {
    (mockAuthService.confirmPasswordReset as jest.Mock).mockRejectedValue(
      new AppError('auth_token_invalid', 'Invalid or expired token', 400),
    );

    submit();

    expect(await screen.findByText('Ungültiger oder abgelaufener Token')).toBeInTheDocument();
  });

  it('zeigt bei einem untypisierten Fehler den Fallback statt dessen message', async () => {
    (mockAuthService.confirmPasswordReset as jest.Mock).mockRejectedValue(
      new Error('Failed to fetch'),
    );

    submit();

    expect(
      await screen.findByText('Passwort konnte nicht zurückgesetzt werden'),
    ).toBeInTheDocument();
  });
});

describe('LoginForm', () => {
  it('übersetzt auch den Fehler des OAuth-Redirects', async () => {
    // The odd one out in this package: this catch wraps no service call at all,
    // only the assignment that navigates to the backend's OAuth endpoint. It
    // still rendered `err.message` with an English literal as its fallback,
    // which is the same leak — found by sweeping the bug class rather than the
    // call graph. Forced here by making the assignment throw, which is the only
    // way this branch is reachable.
    const original = Object.getOwnPropertyDescriptor(window, 'location');
    Object.defineProperty(window, 'location', {
      configurable: true,
      get: () => ({
        set href(_value: string) {
          throw new Error('Navigation blocked by the browser');
        },
      }),
    });

    try {
      render(
        <MemoryRouter>
          <LoginForm />
        </MemoryRouter>,
      );
      fireEvent.click(screen.getByRole('button', { name: /Microsoft/i }));

      expect(await screen.findByText('OAuth-Anmeldung fehlgeschlagen')).toBeInTheDocument();
      expect(screen.queryByText(/Navigation blocked/)).not.toBeInTheDocument();
    } finally {
      if (original) Object.defineProperty(window, 'location', original);
    }
  });
});

describe('ResendVerificationButton', () => {
  function failWith(body: unknown, status = 500): void {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status,
      statusText: 'Error',
      json: async () => body,
    }) as unknown as typeof fetch;
  }

  it('folgt der UI-Sprache, nicht der Sprache der Antwort', async () => {
    // `detail` deliberately French while the UI is German: that is the whole
    // gain of the migration, and the only assertion here that the old code
    // could not also satisfy. The backend answers in the language the *request*
    // carried, which is not necessarily the one the user is reading.
    failWith(
      {
        detail: "L'adresse e-mail est déjà vérifiée",
        error_code: 'auth_email_already_verified',
      },
      400,
    );

    render(<ResendVerificationButton email="user@example.ch" />);
    fireEvent.click(screen.getByRole('button'));

    expect(
      await screen.findByText('E-Mail-Adresse ist bereits verifiziert'),
    ).toBeInTheDocument();
    expect(screen.queryByText("L'adresse e-mail est déjà vérifiée")).not.toBeInTheDocument();
  });

  it('fällt auf den Endpunkt-Code zurück, wenn die Antwort keinen Code trägt', async () => {
    failWith({ detail: 'Internal Server Error' });

    render(<ResendVerificationButton email="user@example.ch" />);
    fireEvent.click(screen.getByRole('button'));

    expect(
      await screen.findByText('Verifizierungs-E-Mail konnte nicht erneut gesendet werden'),
    ).toBeInTheDocument();
  });
});
