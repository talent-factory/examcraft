/**
 * AuthContext (EXAMCRAFT-126): Cookie-Session statt Tokens. Der Zustand ergibt
 * sich aus `GET /api/auth/me`; Login ist eine Weiterleitung auf das Backend.
 */
import React from 'react';
import { render, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import { AppError } from '../../errors';

jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: {
    getLoginUrl: jest.fn(
      (o: { reauth?: boolean; switchAccount?: boolean } = {}) =>
        `http://api.test/api/v1/auth/login${
          o.reauth ? '?reauth=true' : o.switchAccount ? '?switch_account=true' : ''
        }`,
    ),
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

jest.mock('../../i18n', () => ({
  __esModule: true,
  default: {
    changeLanguage: jest.fn().mockResolvedValue(undefined),
    t: (key: string) => key,
  },
}));

jest.mock('../../config/features', () => ({
  SubscriptionTier: { FREE: 'free', STARTER: 'starter', PROFESSIONAL: 'professional', ENTERPRISE: 'enterprise' },
  hasFeature: jest.fn().mockReturnValue(false),
  isFeatureName: jest.fn().mockReturnValue(false),
}));

// eslint-disable-next-line import/first
import AuthService from '../../services/AuthService';
// eslint-disable-next-line import/first
import AdminService from '../../services/AdminService';
// eslint-disable-next-line import/first
import { setLogoutCallback } from '../../api/apiClient';

const mockAuth = AuthService as jest.Mocked<typeof AuthService>;
const mockAdmin = AdminService as jest.Mocked<typeof AdminService>;

const admin = { id: 1, email: 'admin@x.ch', roles: [], is_superuser: false, preferred_language: null };
const target = { id: 2, email: 'user@x.ch', roles: [], is_superuser: false, preferred_language: null };

let latest: ReturnType<typeof useAuth>;
const Probe = () => {
  latest = useAuth();
  return null;
};
const mount = async () => {
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
  await waitFor(() => expect(latest.isLoading).toBe(false));
};

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  mockAuth.logout.mockResolvedValue(undefined);
  mockAdmin.endImpersonation.mockResolvedValue(undefined);
});

describe('AuthContext – Session aus dem Cookie', () => {
  it('lädt beim Mount das Profil über /me und meldet an', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    expect(latest.isAuthenticated).toBe(true);
    expect(latest.user).toEqual(admin);
    expect(latest.isImpersonating).toBe(false);
  });

  it('bleibt abgemeldet bei 401, ohne Fehlermeldung', async () => {
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    expect(latest.isAuthenticated).toBe(false);
    expect(latest.error).toBeNull();
  });

  it('beendet den Ladezustand auch bei einem Netzwerkfehler', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockRejectedValue(new Error('Failed to fetch'));
    await mount();
    expect(latest.isAuthenticated).toBe(false);
    spy.mockRestore();
  });

  it('speichert weder Tokens noch Profil in localStorage', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    expect(localStorage.getItem('examcraft_access_token')).toBeNull();
    expect(localStorage.getItem('examcraft_refresh_token')).toBeNull();
    expect(localStorage.getItem('examcraft_user')).toBeNull();
  });

  it('registriert den lokalen Abbau für 401-Antworten', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    expect(setLogoutCallback).toHaveBeenCalled();
    const clear = (setLogoutCallback as jest.Mock).mock.calls.at(-1)[0];
    await act(async () => {
      await clear();
    });
    expect(latest.isAuthenticated).toBe(false);
    expect(mockAuth.logout).not.toHaveBeenCalled();
  });
});

describe('AuthContext – login/logout', () => {
  const originalLocation = window.location;
  const assign = jest.fn();
  beforeAll(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, assign },
    });
  });
  afterAll(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
  });

  it('login() leitet auf den Backend-Login weiter', async () => {
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    act(() => latest.login());
    expect(assign).toHaveBeenCalledWith('http://api.test/api/v1/auth/login');
  });

  it('login({ reauth }) fordert eine frische Anmeldung an', async () => {
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    act(() => latest.login({ reauth: true }));
    expect(assign).toHaveBeenCalledWith('http://api.test/api/v1/auth/login?reauth=true');
  });

  it('login({ switchAccount }) fordert die Kontoauswahl an', async () => {
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    act(() => latest.login({ switchAccount: true }));
    expect(assign).toHaveBeenCalledWith('http://api.test/api/v1/auth/login?switch_account=true');
  });

  it('logout() beendet die Server-Session und leert den Zustand', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    await act(async () => {
      await latest.logout();
    });
    expect(mockAuth.logout).toHaveBeenCalledTimes(1);
    expect(latest.isAuthenticated).toBe(false);
  });

  it('logout() meldet lokal ab, auch wenn der Server-Aufruf scheitert', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValue(admin as never);
    mockAuth.logout.mockRejectedValue(new Error('offline'));
    await mount();
    await act(async () => {
      await latest.logout();
    });
    expect(latest.isAuthenticated).toBe(false);
    spy.mockRestore();
  });

  it('logout() schreibt den Broadcast-Key für andere Tabs, auch bei Server-Fehler', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValue(admin as never);
    mockAuth.logout.mockRejectedValue(new Error('offline'));
    await mount();
    await act(async () => {
      await latest.logout();
    });
    expect(localStorage.getItem('examcraft_logout_broadcast')).not.toBeNull();
    spy.mockRestore();
  });

  it('ignoriert fremde storage-Keys', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    act(() => {
      window.dispatchEvent(new StorageEvent('storage', { key: 'foo', newValue: '1' }));
    });
    expect(latest.isAuthenticated).toBe(true);
  });

  it('folgt dem Start einer Impersonation aus einem anderen Tab', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    const expiresAt = new Date(Date.now() + 60_000).toISOString();
    localStorage.setItem('examcraft_impersonation_expires_at', expiresAt);
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      window.dispatchEvent(
        new StorageEvent('storage', { key: 'examcraft_impersonation_expires_at', newValue: expiresAt }),
      );
    });
    expect(latest.isImpersonating).toBe(true);
    expect(latest.user?.email).toBe(target.email);
  });

  it('401 während der Impersonation löscht den Hinweis', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    const cb = (setLogoutCallback as jest.Mock).mock.calls.at(-1)[0];
    await act(async () => {
      await cb();
    });
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
    expect(latest.isImpersonating).toBe(false);
  });

  it('folgt einem Logout aus einem anderen Tab', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    act(() => {
      window.dispatchEvent(new StorageEvent('storage', { key: 'examcraft_logout_broadcast', newValue: '1' }));
    });
    expect(latest.isAuthenticated).toBe(false);
  });
});

describe('AuthContext – Impersonation', () => {
  it('übernimmt das Profil des Ziel-Benutzers und merkt sich die Laufzeit', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    expect(latest.isImpersonating).toBe(true);
    expect(latest.user).toEqual(target);
    expect(latest.impersonationExpiresAt).not.toBeNull();
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBe(latest.impersonationExpiresAt);
  });

  it('lehnt eine zweite Impersonation ab', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    await act(async () => {
      await expect(latest.startImpersonation({ expiresIn: 1800 })).rejects.toMatchObject({
        code: 'impersonation_already_active',
      });
    });
  });

  it('schliesst die Server-Session, wenn das Ziel-Profil nicht lädt', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockRejectedValueOnce(new Error('boom'));
    await act(async () => {
      await expect(latest.startImpersonation({ expiresIn: 1800 })).rejects.toThrow('boom');
    });
    expect(mockAdmin.endImpersonation).toHaveBeenCalledTimes(1);
    expect(latest.isImpersonating).toBe(false);
    spy.mockRestore();
  });

  it('endImpersonation() fällt auf das Profil des Admins zurück', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    let result: { backendEndFailed: boolean } | undefined;
    await act(async () => {
      result = await latest.endImpersonation();
    });
    expect(result).toEqual({ backendEndFailed: false });
    expect(latest.isImpersonating).toBe(false);
    expect(latest.user).toEqual(admin);
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
  });

  it('endImpersonation() behält die Impersonation, wenn der Server-Aufruf scheitert', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    mockAdmin.endImpersonation.mockRejectedValueOnce(new Error('offline'));
    let result: { backendEndFailed: boolean } | undefined;
    await act(async () => {
      result = await latest.endImpersonation();
    });
    // The cookie is still valid server-side: banner state and hint must stay.
    expect(result).toEqual({ backendEndFailed: true });
    expect(latest.isImpersonating).toBe(true);
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).not.toBeNull();
    spy.mockRestore();
  });

  it('endImpersonation() fällt lokal zurück, wenn der Server «nicht aktiv» meldet', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    mockAdmin.endImpersonation.mockRejectedValueOnce(
      new AppError('impersonation_not_active', 'not active', 400),
    );
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    let result: { backendEndFailed: boolean } | undefined;
    await act(async () => {
      result = await latest.endImpersonation();
    });
    expect(result).toEqual({ backendEndFailed: false });
    expect(latest.isImpersonating).toBe(false);
    expect(latest.user?.email).toBe(admin.email);
  });

  it('logout() meldet backendEndFailed, wenn das Beenden der Impersonation scheitert', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    mockAdmin.endImpersonation.mockRejectedValueOnce(new Error('offline'));
    let result: unknown;
    await act(async () => {
      result = await latest.logout();
    });
    expect(result).toEqual({ backendEndFailed: true });
    expect(latest.isImpersonating).toBe(true);
    spy.mockRestore();
  });

  it('logout() während der Impersonation beendet nur die Impersonation', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await act(async () => {
      await latest.logout();
    });
    expect(mockAuth.logout).not.toHaveBeenCalled();
    expect(latest.isAuthenticated).toBe(true);
    expect(latest.isImpersonating).toBe(false);
  });

  it('stellt den Banner nach einem Reload aus dem Hinweis wieder her', async () => {
    const expiresAt = new Date(Date.now() + 600_000).toISOString();
    localStorage.setItem('examcraft_impersonation_expires_at', expiresAt);
    mockAuth.getProfile.mockResolvedValue(target as never);
    await mount();
    expect(latest.isImpersonating).toBe(true);
    expect(latest.impersonationExpiresAt).toBe(expiresAt);
  });

  it('ignoriert einen abgelaufenen Hinweis', async () => {
    localStorage.setItem('examcraft_impersonation_expires_at', new Date(Date.now() - 1000).toISOString());
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    expect(latest.isImpersonating).toBe(false);
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
  });
});
