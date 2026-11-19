/**
 * AuthContext (EXAMCRAFT-126): Cookie-Session statt Tokens. Der Zustand ergibt
 * sich aus `GET /api/auth/me`; Login ist eine Weiterleitung auf das Backend.
 */
import React from 'react';
import { render, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import { AppError } from '../../errors';
import { readSessionSnapshot, writeSessionSnapshot } from '../../utils/sessionSnapshot';

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
    expect(latest.notice).toBeNull();
  });

  it('meldet einen 500er beim Start als nicht prüfbare Sitzung', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_profile_load_failed', 'x', 500));
    await mount();
    expect(latest.notice).toBe('session_unavailable');
    spy.mockRestore();
  });

  it('beendet den Ladezustand auch bei einem Netzwerkfehler', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockRejectedValue(new Error('Failed to fetch'));
    await mount();
    expect(latest.isAuthenticated).toBe(false);
    expect(latest.notice).toBe('session_unavailable');
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

describe('AuthContext – checkSession (EXAMCRAFT-136)', () => {
  it('liefert true und behält die Session, solange /me antwortet', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    let ok = false;
    await act(async () => {
      ok = await latest.checkSession();
    });
    expect(ok).toBe(true);
    expect(latest.isAuthenticated).toBe(true);
  });

  it('baut die lokale Session bei 401 ab und liefert false', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    let ok = true;
    await act(async () => {
      ok = await latest.checkSession();
    });
    expect(ok).toBe(false);
    expect(latest.isAuthenticated).toBe(false);
    expect(latest.notice).toBe('session_expired');
  });

  it('der 401-Callback des apiClient setzt «Sitzung abgelaufen» nur bei aktiver Sitzung', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    const callback = (setLogoutCallback as jest.Mock).mock.calls.at(-1)[0];
    await act(async () => {
      await callback();
    });
    expect(latest.isAuthenticated).toBe(false);
    expect(latest.notice).toBe('session_expired');
    // Ein verspätetes 401 darf den Hinweis nicht löschen.
    await act(async () => {
      await callback();
    });
    expect(latest.notice).toBe('session_expired');
  });

  it('der 401-Callback tut ohne Sitzung nichts', async () => {
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    const callback = (setLogoutCallback as jest.Mock).mock.calls.at(-1)[0];
    await act(async () => {
      await callback();
    });
    expect(latest.notice).toBeNull();
  });

  it('wertet einen 500er nicht als Session-Verlust', async () => {
    const spy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_profile_load_failed', 'x', 500));
    let ok = false;
    await act(async () => {
      ok = await latest.checkSession();
    });
    expect(ok).toBe(true);
    expect(latest.isAuthenticated).toBe(true);
    spy.mockRestore();
  });

  it('wertet einen Netzwerkfehler nicht als Session-Verlust', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockRejectedValue(new Error('Failed to fetch'));
    let ok = false;
    await act(async () => {
      ok = await latest.checkSession();
    });
    expect(ok).toBe(true);
    expect(latest.isAuthenticated).toBe(true);
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

  it('logout() meldet einen fehlgeschlagenen Server-Logout als Hinweis', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValue(admin as never);
    mockAuth.logout.mockRejectedValue(new Error('offline'));
    await mount();
    await act(async () => {
      await latest.logout();
    });
    expect(latest.notice).toBe('logout_failed');
    spy.mockRestore();
  });

  it('ein erfolgreicher logout() hinterlässt keinen Hinweis', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    await act(async () => {
      await latest.logout();
    });
    expect(latest.notice).toBeNull();
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

  it('meldet «Sitzung abgelaufen», wenn der Impersonation-Sync aus einem anderen Tab ein 401 trifft', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    localStorage.setItem('examcraft_impersonation_expires_at', new Date(Date.now() + 60_000).toISOString());
    mockAuth.getProfile.mockRejectedValueOnce(new AppError('auth_token_invalid', 'x', 401));
    act(() => {
      window.dispatchEvent(
        new StorageEvent('storage', { key: 'examcraft_impersonation_expires_at', newValue: '1' }),
      );
    });
    await waitFor(() => expect(latest.notice).toBe('session_expired'));
    expect(latest.isAuthenticated).toBe(false);
    spy.mockRestore();
  });

  it('folgt einem Logout aus einem anderen Tab', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    act(() => {
      window.dispatchEvent(new StorageEvent('storage', { key: 'examcraft_logout_broadcast', newValue: '1' }));
    });
    expect(latest.isAuthenticated).toBe(false);
    // Der Benutzer hat sich selbst abgemeldet: kein Hinweis.
    expect(latest.notice).toBeNull();
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

  it('nutzt expiresAt des Servers statt der Client-Uhr für das Ablaufdatum', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800, expiresAt: '2030-01-01T10:30:00Z' });
    });
    expect(latest.impersonationExpiresAt).toBe('2030-01-01T10:30:00.000Z');
  });

  it('fällt ohne gültiges expiresAt auf die Client-Uhr zurück und warnt bei ungültigem Wert', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const now = jest.spyOn(Date, 'now').mockReturnValue(new Date('2030-01-01T10:00:00Z').getTime());
    try {
      mockAuth.getProfile.mockResolvedValueOnce(admin as never);
      await mount();
      mockAuth.getProfile.mockResolvedValueOnce(target as never);
      await act(async () => {
        await latest.startImpersonation({ expiresIn: 1800, expiresAt: 'garbage' });
      });
      expect(latest.impersonationExpiresAt).toBe('2030-01-01T10:30:00.000Z');
      expect(warn).toHaveBeenCalled();
    } finally {
      now.mockRestore();
      warn.mockRestore();
    }
  });

  it('schliesst die verwaiste Session und wirft den Ursprungsfehler, wenn der Cleanup gelingt', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockRejectedValueOnce(new Error('boom'));
    await act(async () => {
      await expect(latest.startImpersonation({ expiresIn: 1800 })).rejects.toThrow('boom');
    });
    expect(mockAdmin.endImpersonation).toHaveBeenCalled();
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
    spy.mockRestore();
  });

  it('wirft den Ursprungsfehler, wenn die verwaiste Session schon beendet ist (401)', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockRejectedValueOnce(new Error('boom'));
    mockAdmin.endImpersonation.mockRejectedValueOnce(new AppError('auth_token_invalid', 'x', 401));
    await act(async () => {
      await expect(latest.startImpersonation({ expiresIn: 1800 })).rejects.toThrow('boom');
    });
    spy.mockRestore();
  });

  it('meldet impersonation_cleanup_failed, wenn die verwaiste Server-Session nicht schliesst', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockRejectedValueOnce(new Error('boom'));
    mockAdmin.endImpersonation.mockRejectedValueOnce(new Error('end failed'));
    await act(async () => {
      await expect(latest.startImpersonation({ expiresIn: 1800 })).rejects.toMatchObject({
        code: 'impersonation_cleanup_failed',
      });
    });
    expect(mockAdmin.endImpersonation).toHaveBeenCalled();
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
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

  it('endImpersonation() meldet «Sitzung abgelaufen», wenn die Admin-Sitzung verloren ist', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    mockAuth.getProfile.mockRejectedValueOnce(new AppError('auth_token_invalid', 'x', 401));
    await act(async () => {
      await latest.endImpersonation();
    });
    expect(latest.isAuthenticated).toBe(false);
    expect(latest.isImpersonating).toBe(false);
    expect(latest.notice).toBe('session_expired');
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
    spy.mockRestore();
  });

  it('endImpersonation() behauptet bei einem Serverfehler keinen Ablauf der Sitzung', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    mockAuth.getProfile.mockRejectedValueOnce(new AppError('auth_profile_load_failed', 'x', 500));
    await act(async () => {
      await latest.endImpersonation();
    });
    expect(latest.isAuthenticated).toBe(false);
    expect(latest.notice).toBe('session_unavailable');
    spy.mockRestore();
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

describe('AuthContext – Impersonation: Hard-Cap und Fehlerpfade (EXAMCRAFT-137)', () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  it('beendet die Impersonation selbst, sobald der Hard-Cap erreicht ist', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    jest.useFakeTimers();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 1800 });
    });
    expect(latest.isImpersonating).toBe(true);

    // Kurz vor Ablauf passiert nichts.
    await act(async () => {
      jest.advanceTimersByTime(1799 * 1000);
    });
    expect(mockAdmin.endImpersonation).not.toHaveBeenCalled();
    expect(latest.isImpersonating).toBe(true);

    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(mockAdmin.endImpersonation).toHaveBeenCalledTimes(1);
    expect(latest.isImpersonating).toBe(false);
    expect(latest.user).toEqual(admin);
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
  });

  it('beendet den Hard-Cap-Timer, wenn die Impersonation vorher manuell endet', async () => {
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    jest.useFakeTimers();
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await act(async () => {
      await latest.startImpersonation({ expiresIn: 60 });
    });
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await act(async () => {
      await latest.endImpersonation();
    });
    mockAdmin.endImpersonation.mockClear();
    await act(async () => {
      jest.advanceTimersByTime(120 * 1000);
    });
    expect(mockAdmin.endImpersonation).not.toHaveBeenCalled();
  });

  it('löscht den Hinweis, wenn die Wiederherstellung beim Start mit 401 scheitert', async () => {
    localStorage.setItem(
      'examcraft_impersonation_expires_at',
      new Date(Date.now() + 600_000).toISOString(),
    );
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
    expect(latest.isImpersonating).toBe(false);
  });

  it('löscht den Hinweis, wenn die Wiederherstellung beim Start mit einem 500er scheitert', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    localStorage.setItem(
      'examcraft_impersonation_expires_at',
      new Date(Date.now() + 600_000).toISOString(),
    );
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_profile_load_failed', 'x', 500));
    await mount();
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
    expect(latest.isImpersonating).toBe(false);
    expect(latest.notice).toBe('session_unavailable');
    spy.mockRestore();
  });

  it('ignoriert einen manipulierten Hinweis (NaN) und entfernt ihn', async () => {
    localStorage.setItem('examcraft_impersonation_expires_at', 'kein-datum');
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    expect(latest.isAuthenticated).toBe(true);
    expect(latest.isImpersonating).toBe(false);
    expect(latest.impersonationExpiresAt).toBeNull();
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
  });

  it('startImpersonation() ohne Admin-Session wird abgelehnt und ändert nichts', async () => {
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    mockAuth.getProfile.mockClear();
    await act(async () => {
      await expect(latest.startImpersonation({ expiresIn: 1800 })).rejects.toMatchObject({
        code: 'impersonation_no_admin_session',
      });
    });
    expect(mockAuth.getProfile).not.toHaveBeenCalled();
    expect(latest.isImpersonating).toBe(false);
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
  });

  it('meldet den ursprünglichen Fehler, auch wenn das Aufräumen der Server-Session scheitert', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await mount();
    mockAuth.getProfile.mockRejectedValueOnce(new Error('profil kaputt'));
    mockAdmin.endImpersonation.mockRejectedValueOnce(new Error('cleanup kaputt'));
    await act(async () => {
      await expect(latest.startImpersonation({ expiresIn: 1800 })).rejects.toThrow('profil kaputt');
    });
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to close orphaned impersonation session'),
        expect.any(Error),
      ),
    );
    expect(latest.isImpersonating).toBe(false);
    expect(latest.isAuthenticated).toBe(true);
    expect(localStorage.getItem('examcraft_impersonation_expires_at')).toBeNull();
    spy.mockRestore();
  });
});

describe('AuthContext – Cross-Tab (EXAMCRAFT-137)', () => {
  it('folgt einem vollständigen Löschen des localStorage (key === null)', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    act(() => {
      window.dispatchEvent(new StorageEvent('storage', { key: null }));
    });
    expect(latest.isAuthenticated).toBe(false);
    // Kein Fehlerhinweis: das Löschen ist keine abgelaufene Sitzung.
    expect(latest.notice).toBeNull();
  });

  it('ein Tab ohne Sitzung ignoriert Logout-Broadcast und Löschen', async () => {
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    // Ohne Sitzung gibt es nichts abzuräumen: fiele die Guard weg, löschte der
    // Handler diesen Snapshot (clearLocalSession), ohne dass sich sonst etwas ändert.
    expect(writeSessionSnapshot('probe', 1, { keep: true })).toBe(true);
    act(() => {
      window.dispatchEvent(new StorageEvent('storage', { key: 'examcraft_logout_broadcast', newValue: '1' }));
      window.dispatchEvent(new StorageEvent('storage', { key: null }));
    });
    expect(latest.isAuthenticated).toBe(false);
    expect(latest.notice).toBeNull();
    expect(readSessionSnapshot('probe', 1)).toEqual({ keep: true });
  });

  it('ein Tab ohne Sitzung lädt bei einem Impersonation-Hinweis kein Profil nach', async () => {
    mockAuth.getProfile.mockRejectedValue(new AppError('auth_token_invalid', 'x', 401));
    await mount();
    mockAuth.getProfile.mockClear();
    act(() => {
      window.dispatchEvent(
        new StorageEvent('storage', { key: 'examcraft_impersonation_expires_at', newValue: '1' }),
      );
    });
    expect(mockAuth.getProfile).not.toHaveBeenCalled();
    expect(latest.isAuthenticated).toBe(false);
  });

  it('folgt dem Ende einer Impersonation aus einem anderen Tab', async () => {
    const expiresAt = new Date(Date.now() + 600_000).toISOString();
    localStorage.setItem('examcraft_impersonation_expires_at', expiresAt);
    mockAuth.getProfile.mockResolvedValueOnce(target as never);
    await mount();
    expect(latest.isImpersonating).toBe(true);

    localStorage.removeItem('examcraft_impersonation_expires_at');
    mockAuth.getProfile.mockResolvedValueOnce(admin as never);
    await act(async () => {
      window.dispatchEvent(
        new StorageEvent('storage', { key: 'examcraft_impersonation_expires_at', newValue: null }),
      );
    });
    await waitFor(() => expect(latest.isImpersonating).toBe(false));
    expect(latest.user).toEqual(admin);
  });

  it('ein Logout während der Impersonation schreibt keinen Broadcast', async () => {
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
    expect(latest.isImpersonating).toBe(false);
    expect(localStorage.getItem('examcraft_logout_broadcast')).toBeNull();
  });
});

describe('AuthContext – Session-Snapshots (EXAMCRAFT-137)', () => {
  const seedSnapshot = () => {
    expect(writeSessionSnapshot('probe', 1, { secret: 'vorheriger Benutzer' })).toBe(true);
    expect(readSessionSnapshot('probe', 1)).not.toBeNull();
  };

  it('logout() räumt die Session-Snapshots ab', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    seedSnapshot();
    await act(async () => {
      await latest.logout();
    });
    expect(readSessionSnapshot('probe', 1)).toBeNull();
  });

  it('räumt die Session-Snapshots auch ab, wenn der Server-Logout scheitert', async () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockAuth.getProfile.mockResolvedValue(admin as never);
    mockAuth.logout.mockRejectedValue(new Error('offline'));
    await mount();
    seedSnapshot();
    await act(async () => {
      await latest.logout();
    });
    expect(readSessionSnapshot('probe', 1)).toBeNull();
    spy.mockRestore();
  });

  it('ein 401 räumt die Session-Snapshots ab', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    seedSnapshot();
    const callback = (setLogoutCallback as jest.Mock).mock.calls.at(-1)[0];
    await act(async () => {
      await callback();
    });
    expect(readSessionSnapshot('probe', 1)).toBeNull();
  });

  it('ein Logout in einem anderen Tab räumt die Session-Snapshots ab', async () => {
    mockAuth.getProfile.mockResolvedValue(admin as never);
    await mount();
    seedSnapshot();
    act(() => {
      window.dispatchEvent(new StorageEvent('storage', { key: 'examcraft_logout_broadcast', newValue: '1' }));
    });
    expect(readSessionSnapshot('probe', 1)).toBeNull();
  });
});
