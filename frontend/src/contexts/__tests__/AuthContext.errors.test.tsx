import React from 'react';
import { render, act } from '@testing-library/react';

import { AppError } from '../../errors';
import { AuthProvider, useAuth } from '../AuthContext';

/**
 * `AuthContext` is the only consumer of `AuthService` that does not render the
 * message itself — it parks it in `state.error`, and four components
 * (LoginForm, RegisterForm, ProfileEdit, PasswordChange) render that string in
 * an `<Alert>`. So this is where the `err.message` leak lived: the raw value
 * reached the UI one hop later, which is exactly why grepping the components
 * for `.message` never showed it (TF-772 PR 3).
 *
 * Unlike every other consumer in this package, the translation here goes
 * through the `i18n` singleton rather than `useTranslation()` — a context
 * provider has no hook to call, and `AuthContext` already imports the
 * singleton for `changeLanguage`. The consequence is that the stored sentence
 * is frozen in the language that was active when the call failed. That is not
 * new (the field has always held a plain string) and it is short-lived: the
 * four consumers clear it on the next input.
 */

jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: {
    login: jest.fn(),
    register: jest.fn(),
    refreshToken: jest.fn(),
    getProfile: jest.fn(),
    updateProfile: jest.fn(),
    setPassword: jest.fn(),
    changePassword: jest.fn(),
    logout: jest.fn().mockResolvedValue(undefined),
  },
}));

jest.mock('../../services/AdminService', () => ({
  __esModule: true,
  default: { endImpersonation: jest.fn().mockResolvedValue(undefined) },
}));

jest.mock('../../api/apiClient', () => ({
  setTokenRefreshCallback: jest.fn(),
  setLogoutCallback: jest.fn(),
  setAdoptStoredTokensCallback: jest.fn(),
  setupFetchInterceptor: jest.fn(),
  executeTokenRefresh: jest.fn().mockResolvedValue(undefined),
}));

// The real German bundle, reached through the same singleton the provider
// uses. A mock that echoed the key back would make every assertion below pass
// through translateError's fallback branch instead of its success branch —
// `t(key) !== key` is how a missing translation is detected.
jest.mock('../../i18n', () => {
  const de = require('../../locales/de/translation.json');
  const resolve = (key: string): string =>
    key.split('.').reduce<unknown>(
      (cur, part) =>
        cur != null && typeof cur === 'object'
          ? (cur as Record<string, unknown>)[part]
          : undefined,
      de,
    ) as string ?? key;
  return {
    __esModule: true,
    default: {
      changeLanguage: jest.fn().mockResolvedValue(undefined),
      t: (key: string) => resolve(key) ?? key,
    },
  };
});

jest.mock('../../config/features', () => ({
  SubscriptionTier: {
    FREE: 'free',
    STARTER: 'starter',
    PROFESSIONAL: 'professional',
    ENTERPRISE: 'enterprise',
  },
  hasFeature: jest.fn().mockReturnValue(false),
  isFeatureName: jest.fn().mockReturnValue(false),
}));

// eslint-disable-next-line import/first
import AuthService from '../../services/AuthService';

const mockAuthService = AuthService as jest.Mocked<typeof AuthService>;

function AuthConsumer({
  onContext,
}: {
  onContext: (auth: ReturnType<typeof useAuth>) => void;
}) {
  const auth = useAuth();
  React.useEffect(() => {
    onContext(auth);
  });
  return null;
}

async function mountAuthProvider(): Promise<() => ReturnType<typeof useAuth>> {
  let latest: ReturnType<typeof useAuth> | undefined;
  render(
    <AuthProvider>
      <AuthConsumer onContext={(auth) => { latest = auth; }} />
    </AuthProvider>,
  );
  await act(async () => {
    await Promise.resolve();
  });
  return () => latest as ReturnType<typeof useAuth>;
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  (mockAuthService.logout as jest.Mock).mockResolvedValue(undefined);
});

describe('AuthContext — Fehlermeldungen sind übersetzt, nicht durchgereicht', () => {
  it('übersetzt den Code eines fehlgeschlagenen Logins', async () => {
    (mockAuthService.login as jest.Mock).mockRejectedValue(
      new AppError('auth_invalid_credentials', 'Invalid email or password', 401),
    );
    const auth = await mountAuthProvider();

    await act(async () => {
      await expect(auth().login({ email: 'a@b.ch', password: 'x' })).rejects.toBeTruthy();
    });

    expect(auth().error).toBe('Ungültige E-Mail oder Passwort');
  });

  it('zeigt bei einem untypisierten Fehler den Fallback statt dessen message', async () => {
    // The regression this guards: `new Error('Failed to fetch')` is what a
    // dropped connection produces, and its message is both English and
    // meaningless to a user. Before TF-772 it was rendered verbatim.
    (mockAuthService.login as jest.Mock).mockRejectedValue(new Error('Failed to fetch'));
    const auth = await mountAuthProvider();

    await act(async () => {
      await expect(auth().login({ email: 'a@b.ch', password: 'x' })).rejects.toBeTruthy();
    });

    expect(auth().error).toBe('Anmeldung fehlgeschlagen');
    expect(auth().error).not.toContain('Failed to fetch');
  });

  it('übersetzt den Code einer fehlgeschlagenen Registrierung', async () => {
    (mockAuthService.register as jest.Mock).mockRejectedValue(
      new AppError('auth_email_taken', 'Email address is already registered', 409),
    );
    const auth = await mountAuthProvider();

    await act(async () => {
      await expect(
        auth().register({
          email: 'a@b.ch',
          password: 'x',
          first_name: 'A',
          last_name: 'B',
        } as never),
      ).rejects.toBeTruthy();
    });

    expect(auth().error).toBe('E-Mail-Adresse ist bereits registriert');
  });

  it('übersetzt den Code einer fehlgeschlagenen Passwortänderung', async () => {
    // Needs a real session first: changePassword short-circuits without an
    // access token, and that guard has its own error path (below).
    (mockAuthService.login as jest.Mock).mockResolvedValue({
      access_token: 'access',
      refresh_token: 'refresh',
    });
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue({
      id: 1,
      email: 'a@b.ch',
      preferred_language: null,
    });
    (mockAuthService.changePassword as jest.Mock).mockRejectedValue(
      new AppError('auth_password_incorrect', 'Current password is incorrect', 400),
    );
    const auth = await mountAuthProvider();

    await act(async () => {
      await auth().login({ email: 'a@b.ch', password: 'x' });
    });
    await act(async () => {
      await expect(
        auth().changePassword({ current_password: 'a', new_password: 'b' } as never),
      ).rejects.toBeTruthy();
    });

    expect(auth().error).toBe('Aktuelles Passwort ist falsch');
  });

  it('meldet die fehlende Sitzung als abgelaufenen Token, nicht als "Not authenticated"', async () => {
    // The guard in updateProfile/setPassword/changePassword threw a bare
    // `new Error('Not authenticated')`, and `state.error` carried that English
    // developer string straight into the four <Alert>s. It has a UI path, so
    // the TF-295 "developer errors stay English" exemption does not cover it.
    const auth = await mountAuthProvider();

    await act(async () => {
      await expect(auth().updateProfile({ first_name: 'A' })).rejects.toBeTruthy();
    });

    expect(auth().error).toBe('Ungültiger oder abgelaufener Token');
  });
});
