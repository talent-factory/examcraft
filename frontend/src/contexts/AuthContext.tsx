/**
 * Authentication Context
 * Global auth state management with React Context
 *
 * EXAMCRAFT-126: Die Anmeldung ist eine serverseitige Session (BFF, OIDC über
 * tessera/Zitadel). Der Browser hält nur ein httpOnly-Cookie; es gibt keine
 * Tokens, keinen Refresh und keine Passwort-Formulare mehr. Der Zustand ergibt
 * sich aus `GET /api/auth/me`.
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  AuthState,
  AuthContextType,
  UserRole,
  UpdateProfileRequest,
  AuthNotice,
} from '../types/auth';
import AuthService from '../services/AuthService';
import AdminService from '../services/AdminService';
import { resolveLanguageOnProfileLoad } from '../utils/languagePreference';
import i18n from '../i18n';
import { AppError, translateError } from '../errors';
import type { ErrorParams } from '../errors';
import { SubscriptionTier, hasFeature as tierHasFeature, isFeatureName } from '../config/features';
import { setLogoutCallback, setupFetchInterceptor } from '../api/apiClient';
import { clearAllSessionSnapshots } from '../utils/sessionSnapshot';

// ============================================================================
// Context Creation
// ============================================================================

/**
 * `translateError` needs a `t`; a context provider has no `useTranslation()`
 * to call. The i18n singleton this file already imports for `changeLanguage`
 * supplies one. Wrapped rather than passed as `i18n.t`, so the call keeps its
 * receiver and so the overloaded i18next signature narrows to the plain
 * `(key, params) => string` that `Translate` asks for.
 *
 * `state.error` therefore holds a sentence frozen in the language that was
 * active when the call failed; its consumers clear it via `clearError()`.
 */
const translate = (key: string, params?: ErrorParams): string => i18n.t(key, params);

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================================================
// Local Storage Keys
// ============================================================================

// Written only by an intentional logout(). Other tabs' `storage` listener
// follows it, so a logout in one tab ends the UI session in all of them. The
// cookie is shared by the browser anyway; this only syncs the visible state.
const LOGOUT_BROADCAST_KEY = 'examcraft_logout_broadcast';

// UI hint only: when the running impersonation ends (ISO timestamp). The truth
// is the server-side impersonation cookie; `/api/auth/me` does not say whether
// the profile belongs to an impersonated user, so the banner survives a reload
// through this hint. Tab-independent, because the cookie is too.
const IMPERSONATION_EXPIRES_KEY = 'examcraft_impersonation_expires_at';

const NOT_IMPERSONATING = { isImpersonating: false, impersonationExpiresAt: null } as const;

const SIGNED_OUT: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  notice: null,
  ...NOT_IMPERSONATING,
};

function signedInState(user: AuthState['user'], impersonationExpiresAt: string | null): AuthState {
  return {
    user,
    isAuthenticated: true,
    isLoading: false,
    error: null,
    notice: null,
    isImpersonating: impersonationExpiresAt !== null,
    impersonationExpiresAt,
  };
}

/** The server reports that there is no impersonation left to end. */
function isImpersonationAlreadyEnded(error: unknown): boolean {
  return (
    error instanceof AppError &&
    (error.status === 401 || (error.status === 400 && error.code === 'impersonation_not_active'))
  );
}

function readImpersonationHint(): string | null {
  try {
    const value = localStorage.getItem(IMPERSONATION_EXPIRES_KEY);
    if (value && new Date(value).getTime() > Date.now()) return value;
    if (value) localStorage.removeItem(IMPERSONATION_EXPIRES_KEY);
  } catch (error) {
    console.error('[AuthContext] Failed to read impersonation hint:', error);
  }
  return null;
}

function writeImpersonationHint(expiresAt: string | null): void {
  try {
    if (expiresAt) localStorage.setItem(IMPERSONATION_EXPIRES_KEY, expiresAt);
    else localStorage.removeItem(IMPERSONATION_EXPIRES_KEY);
  } catch (error) {
    console.error('[AuthContext] Failed to persist impersonation hint:', error);
  }
}

// ============================================================================
// Auth Provider Component
// ============================================================================

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    ...SIGNED_OUT,
    isLoading: true,
  });

  const isAuthenticatedRef = useRef(false);
  const isImpersonatingRef = useRef(false);
  const impersonationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const endImpersonationRef = useRef<() => Promise<{ backendEndFailed: boolean }>>(
    async () => ({ backendEndFailed: false }),
  );

  useEffect(() => {
    isAuthenticatedRef.current = state.isAuthenticated;
  }, [state.isAuthenticated]);

  useEffect(() => {
    isImpersonatingRef.current = state.isImpersonating;
  }, [state.isImpersonating]);

  const cancelImpersonationTimer = useCallback(() => {
    if (impersonationTimerRef.current) {
      clearTimeout(impersonationTimerRef.current);
      impersonationTimerRef.current = null;
    }
  }, []);

  /**
   * Tear the session down in this tab only (state + hints). Does not call the
   * backend: used when the server already said the session is gone (401) and
   * when another tab logged out. `notice` tells the login page why the user
   * lands there (EXAMCRAFT-135); without one the sign-out is silent.
   */
  const clearLocalSession = useCallback((notice: AuthNotice | null = null) => {
    cancelImpersonationTimer();
    writeImpersonationHint(null);
    // TF-608: sessionStorage survives a user switch within the same tab;
    // rationale (shared machine) in sessionSnapshot.ts.
    clearAllSessionSnapshots();
    // Update the ref right away: the effect that mirrors the state runs only
    // after the commit, and a late 401 must not count as an expiry meanwhile.
    isAuthenticatedRef.current = false;
    setState({ ...SIGNED_OUT, notice });
  }, [cancelImpersonationTimer]);

  // Sets the ref in the same step as the state: the effect that mirrors the
  // state runs only after the commit, and a 401 arriving in between must still
  // find the session it has to end.
  const applySignedIn = useCallback((user: AuthState['user'], impersonationExpiresAt: string | null) => {
    isAuthenticatedRef.current = true;
    setState(signedInState(user, impersonationExpiresAt));
  }, []);

  // A 401 on a session the user was still using means it expired or was ended
  // elsewhere. Without a running session (public pages, the login page itself,
  // late 401s of requests still in flight after the sign-out) there is nothing
  // to tear down, and resetting would wipe the notice the first 401 set.
  const endExpiredSession = useCallback(() => {
    if (!isAuthenticatedRef.current) return;
    clearLocalSession('session_expired');
  }, [clearLocalSession]);

  /**
   * Load the profile of the session cookie and apply the preferred language.
   * Rejects when there is no valid session (401) or the request fails.
   */
  const loadProfile = useCallback(async () => {
    const profile = await AuthService.getProfile();

    // See resolveLanguageOnProfileLoad's own doc for why this — not the
    // raw account value — is what gets applied here.
    const language = resolveLanguageOnProfileLoad(profile.preferred_language);
    if (language) {
      await i18n.changeLanguage(language).catch((e: unknown) =>
        console.error('[AuthContext] Failed to apply preferred language:', e)
      );
    }
    return profile;
  }, []);

  const scheduleImpersonationEnd = useCallback((expiresAt: string) => {
    cancelImpersonationTimer();
    const delay = Math.max(new Date(expiresAt).getTime() - Date.now(), 0);
    // Hard cap of the impersonation (TF-741): the server drops it by itself;
    // falling back to the admin's profile keeps the banner honest.
    impersonationTimerRef.current = setTimeout(() => {
      endImpersonationRef.current().catch((err) =>
        console.error('[AuthContext] Automatic impersonation end failed:', err)
      );
    }, delay);
  }, [cancelImpersonationTimer]);

  /**
   * Restore the session from the cookie on mount.
   */
  useEffect(() => {
    let cancelled = false;
    const restore = async () => {
      try {
        const profile = await loadProfile();
        if (cancelled) return;
        const expiresAt = readImpersonationHint();
        applySignedIn(profile, expiresAt);
        if (expiresAt) scheduleImpersonationEnd(expiresAt);
      } catch (error) {
        // 401 is the normal "not signed in"; anything else is logged and
        // reported on the login page, since the user may well have a valid
        // session that just could not be checked (backend or network down).
        // Either way the app shows the login page rather than hanging on the
        // spinner.
        const notSignedIn = error instanceof AppError && error.status === 401;
        if (!notSignedIn) {
          console.error('[AuthContext] Failed to load session:', error);
        }
        if (!cancelled) {
          writeImpersonationHint(null);
          setState({ ...SIGNED_OUT, notice: notSignedIn ? null : 'session_unavailable' });
        }
      }
    };
    restore();
    return () => {
      cancelled = true;
    };
  }, [applySignedIn, loadProfile, scheduleImpersonationEnd]);

  /**
   * Start the login: the backend runs the OIDC flow and sets the cookie, then
   * redirects back to the app.
   */
  const login = useCallback((
    options: { reauth?: boolean; switchAccount?: boolean; returnTo?: string } = {},
  ) => {
    window.location.assign(AuthService.getLoginUrl(options));
  }, []);

  /**
   * Logout
   */
  const logout = useCallback(async (): Promise<{ backendEndFailed: boolean } | void> => {
    // TF-743: logging out while impersonating only ends the impersonation
    // (the backend does the same); the admin stays signed in.
    if (isImpersonatingRef.current) {
      return endImpersonationRef.current();
    }

    let notice: AuthNotice | null = null;
    try {
      await AuthService.logout();
    } catch (error) {
      // The local session is torn down regardless, but the server-side one
      // may still be alive: say so instead of pretending a clean sign-out.
      console.error('[AuthContext] Logout error:', error);
      notice = 'logout_failed';
    } finally {
      try {
        localStorage.setItem(LOGOUT_BROADCAST_KEY, String(Date.now()));
      } catch (error) {
        console.error('[AuthContext] Failed to broadcast logout:', error);
      }
      clearLocalSession(notice);
    }
  }, [clearLocalSession]);

  /**
   * Take over an impersonation the backend just started (it set the
   * impersonation cookie): load the target's profile and remember the cap.
   */
  const startImpersonation = useCallback(async (payload: { expiresIn: number; expiresAt?: string }) => {
    if (isImpersonatingRef.current) {
      // A second impersonation on top of an active one is refused by the
      // backend as well; stop before the banner state gets confused.
      throw new AppError('impersonation_already_active');
    }
    if (!isAuthenticatedRef.current) {
      throw new AppError('impersonation_no_admin_session');
    }

    // Server clock first (EXAMCRAFT-139): the cap is enforced server-side, so a
    // skewed client clock must not shift the banner. The client clock is only
    // the fallback for a response without (or with an invalid) `expires_at`.
    const serverExpiry = payload.expiresAt ? new Date(payload.expiresAt) : null;
    if (serverExpiry && Number.isNaN(serverExpiry.getTime())) {
      console.warn('[AuthContext] Invalid impersonation expires_at, using client clock:', payload.expiresAt);
    }
    const expiresAt =
      serverExpiry && !Number.isNaN(serverExpiry.getTime())
        ? serverExpiry.toISOString()
        : new Date(Date.now() + payload.expiresIn * 1000).toISOString();
    try {
      const targetUser = await loadProfile();
      writeImpersonationHint(expiresAt);
      applySignedIn(targetUser, expiresAt);
      scheduleImpersonationEnd(expiresAt);
    } catch (error) {
      // The backend session already exists; tell it the attempt is abandoned
      // instead of leaving it open until the cap / reaper ends it.
      console.error('[AuthContext] Starting impersonation failed:', error);
      cancelImpersonationTimer();
      writeImpersonationHint(null);
      try {
        await AdminService.endImpersonation();
      } catch (endError) {
        // Nothing left to close (session already gone): the original error is
        // the real problem, not a dangling server session.
        if (isImpersonationAlreadyEnded(endError)) throw error;
        // The server-side impersonation stays open (cookie valid, no banner):
        // tell the admin instead of failing silently (EXAMCRAFT-139).
        console.error('[AuthContext] Failed to close orphaned impersonation session:', endError);
        throw new AppError('impersonation_cleanup_failed', String(error));
      }
      throw error;
    }
  }, [applySignedIn, cancelImpersonationTimer, loadProfile, scheduleImpersonationEnd]);

  /**
   * Public entry point for ending impersonation (banner button, hard cap,
   * logout while impersonating). The banner state is kept when the backend
   * call fails (the cookie is still valid), except when the server reports
   * that there is nothing left to end.
   */
  const endImpersonation = useCallback(async (): Promise<{ backendEndFailed: boolean }> => {
    if (!isImpersonatingRef.current) return { backendEndFailed: false };

    try {
      await AdminService.endImpersonation();
    } catch (error) {
      // Nothing left to end (hard cap passed, reaper closed it, session gone):
      // the server already acts as the admin, so fall back locally.
      if (!isImpersonationAlreadyEnded(error)) {
        // The impersonation cookie is still valid, so every request keeps
        // running as the target user. Keep banner, hint and timer: hiding them
        // would show the admin as back while the server still acts as someone else.
        console.error('[AuthContext] Failed to end impersonation server-side:', error);
        return { backendEndFailed: true };
      }
    }

    cancelImpersonationTimer();
    writeImpersonationHint(null);
    const backendEndFailed = false;

    try {
      const adminUser = await loadProfile();
      applySignedIn(adminUser, null);
    } catch (error) {
      // No valid session left (e.g. the admin's own session lapsed).
      console.error('[AuthContext] Failed to reload admin profile after impersonation:', error);
      // Only a 401 means the session is gone; any other failure just means it
      // could not be checked, and the notice must not claim an expiry.
      clearLocalSession(
        error instanceof AppError && error.status === 401 ? 'session_expired' : 'session_unavailable',
      );
    }
    return { backendEndFailed };
  }, [applySignedIn, cancelImpersonationTimer, loadProfile, clearLocalSession]);

  useEffect(() => {
    endImpersonationRef.current = endImpersonation;
  }, [endImpersonation]);

  useEffect(() => {
    // The api client reaches for this on a 401 from any request: the cookie is
    // gone or expired, so only the local state is torn down.
    setLogoutCallback(async () => endExpiredSession());
    setupFetchInterceptor();
  }, [endExpiredSession]);

  /**
   * Follow a logout made in another tab.
   */
  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      // The impersonation cookie is shared by all tabs, so a start or end in
      // another tab changes who this tab acts as: reload the profile and follow
      // the hint (EXAMCRAFT-126).
      if (event.key === IMPERSONATION_EXPIRES_KEY) {
        if (!isAuthenticatedRef.current) return;
        loadProfile()
          .then((profile) => {
            const expiresAt = readImpersonationHint();
            applySignedIn(profile, expiresAt);
            if (expiresAt) scheduleImpersonationEnd(expiresAt);
            else cancelImpersonationTimer();
          })
          .catch((error) => {
            console.error('[AuthContext] Failed to sync impersonation from another tab:', error);
            // The session ended meanwhile: say so instead of keeping a stale identity.
            if (error instanceof AppError && error.status === 401) endExpiredSession();
          });
        return;
      }

      const isFullClear = event.key === null;
      if (!isFullClear && event.key !== LOGOUT_BROADCAST_KEY) return;
      if (!isAuthenticatedRef.current) return;
      clearLocalSession();
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [applySignedIn, clearLocalSession, endExpiredSession, loadProfile, scheduleImpersonationEnd, cancelImpersonationTimer]);

  useEffect(() => cancelImpersonationTimer, [cancelImpersonationTimer]);

  /**
   * Update user profile
   */
  const updateProfile = useCallback(async (data: UpdateProfileRequest) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const user = await AuthService.updateProfile(data);

      setState(prev => ({
        ...prev,
        user,
        isLoading: false,
      }));
    } catch (error) {
      const errorMessage = translateError(error, translate, 'errors.auth_profile_update_failed');
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, []);

  /**
   * 401 on `/api/auth/me` ends the local session; any other outcome keeps it.
   */
  const checkSession = useCallback(async (): Promise<boolean> => {
    try {
      await AuthService.getProfile();
      return true;
    } catch (error) {
      // `/api/auth/me` is excluded from the global 401 handling, so the
      // teardown happens here.
      if (error instanceof AppError && error.status === 401) {
        endExpiredSession();
        return false;
      }
      console.warn('[AuthContext] Session check failed, keeping the session:', error);
      return true;
    }
  }, [endExpiredSession]);

  /**
   * Clear error
   */
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  /**
   * Check if user has specific permission
   * Checks BOTH role-based permissions AND subscription tier features
   */
  const hasPermission = useCallback((permission: string): boolean => {
    if (!state.user) return false;
    if (state.user.is_superuser) return true;

    // First: Check if it's a subscription tier feature
    if (isFeatureName(permission)) {
      const institution = state.user.institution;
      if (institution && institution.subscription_tier) {
        const tier = institution.subscription_tier as SubscriptionTier;
        if (tierHasFeature(tier, permission)) {
          return true;
        }
      }
    }

    // Second: Check role-based permissions
    if (!state.user.roles || !Array.isArray(state.user.roles)) return false;

    return state.user.roles.some(role => {
      // Ensure permissions is an array before checking
      if (!role.permissions || !Array.isArray(role.permissions)) return false;
      return role.permissions.includes(permission);
    });
  }, [state.user]);

  /**
   * Check if user has specific role
   */
  const hasRole = useCallback((role: UserRole): boolean => {
    if (!state.user) return false;

    // Guard against undefined roles
    if (!state.user.roles || !Array.isArray(state.user.roles)) return false;

    return state.user.roles.some(r => r.name === role);
  }, [state.user]);

  const value: AuthContextType = {
    ...state,
    login,
    logout,
    updateProfile,
    checkSession,
    clearError,
    hasPermission,
    hasRole,
    startImpersonation,
    endImpersonation,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// ============================================================================
// Custom Hook
// ============================================================================

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
