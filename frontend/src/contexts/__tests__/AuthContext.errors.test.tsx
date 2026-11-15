import React from 'react';
import { render, act } from '@testing-library/react';

import { AppError } from '../../errors';
import { AuthProvider, useAuth } from '../AuthContext';

/**
 * `AuthContext` is the only consumer of `AuthService` that does not render the
 * message itself — it parks it in `state.error`, and ProfileEdit renders
 * that string in an `<Alert>`. So this is where the `err.message` leak lived: the raw value
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
    getLoginUrl: jest.fn(),
    getProfile: jest.fn(),
    updateProfile: jest.fn(),
    logout: jest.fn().mockResolvedValue(undefined),
  },
}));

jest.mock('../../services/AdminService', () => ({
  __esModule: true,
  default: { endImpersonation: jest.fn().mockResolvedValue(undefined) },
}));

jest.mock('../../api/apiClient', () => ({
  setLogoutCallback: jest.fn(),
  setupFetchInterceptor: jest.fn(),
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
  beforeEach(() => {
    (mockAuthService.getProfile as jest.Mock).mockResolvedValue({
      id: 1,
      email: 'a@b.ch',
      preferred_language: null,
    });
  });

  it('übersetzt den Code eines fehlgeschlagenen Profil-Updates', async () => {
    (mockAuthService.updateProfile as jest.Mock).mockRejectedValue(
      new AppError('auth_email_taken', 'Email address is already registered', 409),
    );
    const auth = await mountAuthProvider();

    await act(async () => {
      await expect(auth().updateProfile({ email: 'a@b.ch' })).rejects.toBeTruthy();
    });

    expect(auth().error).toBe('E-Mail-Adresse ist bereits registriert');
  });

  it('zeigt bei einem untypisierten Fehler den Fallback statt dessen message', async () => {
    // `new Error('Failed to fetch')` is what a dropped connection produces; its
    // message is English and meaningless to a user (TF-772).
    (mockAuthService.updateProfile as jest.Mock).mockRejectedValue(new Error('Failed to fetch'));
    const auth = await mountAuthProvider();

    await act(async () => {
      await expect(auth().updateProfile({ first_name: 'A' })).rejects.toBeTruthy();
    });

    expect(auth().error).toBe('Profil konnte nicht aktualisiert werden');
    expect(auth().error).not.toContain('Failed to fetch');
  });
});
