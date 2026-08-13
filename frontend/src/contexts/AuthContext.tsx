/**
 * Authentication Context
 * Global auth state management with React Context
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  AuthState,
  AuthContextType,
  UserRole,
  RegisterRequest,
  UpdateProfileRequest,
  ChangePasswordRequest,
} from '../types/auth';
import AuthService from '../services/AuthService';
import i18n from '../i18n';
import { SubscriptionTier, hasFeature as tierHasFeature, isFeatureName } from '../config/features';
import {
  setTokenRefreshCallback,
  setLogoutCallback,
  setAdoptStoredTokensCallback,
  setupFetchInterceptor,
  executeTokenRefresh,
} from '../api/apiClient';
import {
  withTokenRefreshLock,
  getTokenRemainingMs,
  REFRESH_LEAD_MS,
  ACCESS_TOKEN_KEY,
} from '../api/tokenRefreshLock';

// ============================================================================
// Context Creation
// ============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================================================
// Local Storage Keys
// ============================================================================

const REFRESH_TOKEN_KEY = 'examcraft_refresh_token';
const USER_KEY = 'examcraft_user';

// Written only by an intentional, backend-revoking logout() — never by
// clearLocalSession() on its own. Other tabs' `storage` listener uses this to
// tell "the backend already revoked every session, follow it" apart from "my
// own refresh attempt just failed", which is not proof the session is dead
// (TF-607).
const LOGOUT_BROADCAST_KEY = 'examcraft_logout_broadcast';

// ============================================================================
// Auth Provider Component
// ============================================================================

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshAccessTokenRef = useRef<() => Promise<void>>(async () => {});
  const scheduleTokenRefreshRef = useRef<(token: string) => void>(() => {});
  const isAuthenticatedRef = useRef(false);
  // Mirrors state.{accessToken,refreshToken} for the storage listener below,
  // which runs outside React's render cycle and needs this tab's current,
  // still-valid tokens without taking a dependency that would re-subscribe
  // the listener on every token refresh.
  const currentTokensRef = useRef<{ accessToken: string | null; refreshToken: string | null }>({
    accessToken: null,
    refreshToken: null,
  });

  useEffect(() => {
    isAuthenticatedRef.current = state.isAuthenticated;
  }, [state.isAuthenticated]);

  useEffect(() => {
    currentTokensRef.current = {
      accessToken: state.accessToken,
      refreshToken: state.refreshToken,
    };
  }, [state.accessToken, state.refreshToken]);

  const cancelRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  /**
   * Tear the session down in this tab only.
   *
   * Deliberately does NOT call AuthService.logout(): that endpoint revokes
   * *every* session of the user on the backend, so using it as the reaction
   * to a failed refresh would sign the user out on all their other tabs and
   * devices too (TF-607). Only an explicit user logout may do that.
   */
  const clearLocalSession = useCallback(() => {
    cancelRefreshTimer();

    try {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch (error) {
      // Safari private mode / storage-quota policies can make localStorage
      // writes throw. Even then, this tab's own state must still flip to
      // logged-out — an uncaught throw here would leave isAuthenticated
      // stuck at true while every subsequent request silently fails.
      console.error('[AuthContext] Failed to clear stored session:', error);
    } finally {
      setState({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  }, [cancelRefreshTimer]);

  /**
   * Pull tokens another tab just rotated into this tab's state and re-arm the
   * refresh timer for the new expiry. Returns false if no usable pair is
   * stored.
   */
  const adoptStoredTokens = useCallback((): boolean => {
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!accessToken || !refreshToken) return false;

    setState(prev =>
      prev.accessToken === accessToken && prev.refreshToken === refreshToken
        ? prev
        : { ...prev, accessToken, refreshToken }
    );
    scheduleTokenRefreshRef.current(accessToken);
    return true;
  }, []);

  const scheduleTokenRefresh = useCallback((accessToken: string) => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
    const fireRefresh = () => {
      // Route through executeTokenRefresh so the proactive timer shares the
      // same in-flight promise as the reactive 401 interceptors. Without
      // this, a 401 arriving while the timer fires would trigger a parallel
      // refresh and the rotating-refresh-token backend would invalidate one.
      executeTokenRefresh('proactive-timer').catch((err) => {
        console.error('[AuthContext] Proactive refresh failed:', err);
      });
    };
    const remaining = getTokenRemainingMs(accessToken);
    const delay = remaining === null ? -1 : remaining - REFRESH_LEAD_MS;
    if (delay > 0) {
      refreshTimerRef.current = setTimeout(fireRefresh, delay);
    } else {
      // Either the token is already inside the safety window or it could not
      // be parsed. Either way, try to refresh now — the refresh endpoint is
      // the only authority that can tell us whether the session is still
      // valid.
      fireRefresh();
    }
  }, []);

  /**
   * Load auth state from localStorage on mount
   */
  useEffect(() => {
    const loadAuthState = async () => {
      try {
        const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

        if (accessToken && refreshToken) {
          // Always fetch fresh profile instead of relying on cached user
          try {
            // Add timeout to prevent spinner from hanging
            const timeoutPromise = new Promise((_, reject) =>
              setTimeout(() => reject(new Error('Profile fetch timeout')), 5000)
            );

            const profile = await Promise.race([
              AuthService.getProfile(accessToken),
              timeoutPromise
            ]) as any;

            // Update localStorage with fresh user data
            localStorage.setItem(USER_KEY, JSON.stringify(profile));

            if (profile.preferred_language) {
              await i18n.changeLanguage(profile.preferred_language).catch((e: unknown) =>
                console.error('[AuthContext] Failed to apply preferred language:', e)
              );
            }

            setState({
              user: profile,
              accessToken,
              refreshToken,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
            scheduleTokenRefreshRef.current(accessToken);
          } catch (error) {
            console.error('[AuthContext] Token verification failed:', error);

            // Persist a token pair, then load its profile and publish both as
            // our session. Persisting *before* the profile fetch matters: the
            // refresh above already consumed the old refresh token on the
            // backend, so other tabs queued behind the cross-tab lock need
            // this pair in localStorage to adopt — even if the profile fetch
            // that follows times out or fails.
            const applyTokens = async (access: string, refresh: string) => {
              localStorage.setItem(ACCESS_TOKEN_KEY, access);
              localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
              scheduleTokenRefreshRef.current(access);

              const profileTimeoutPromise = new Promise<never>((_, reject) =>
                setTimeout(() => reject(new Error('Profile fetch timeout')), 5000)
              );

              const profile = await Promise.race([
                AuthService.getProfile(access),
                profileTimeoutPromise
              ]) as any;

              localStorage.setItem(USER_KEY, JSON.stringify(profile));

              if (profile.preferred_language) {
                await i18n.changeLanguage(profile.preferred_language).catch((e: unknown) =>
                  console.error('[AuthContext] Failed to apply preferred language:', e)
                );
              }

              setState({
                user: profile,
                accessToken: access,
                refreshToken: refresh,
                isAuthenticated: true,
                isLoading: false,
                error: null,
              });
            };

            // Token expired, try to refresh — under the cross-tab lock. Opening
            // several tabs at once mounts several providers at once, and each
            // would otherwise send the same refresh token; the rotating backend
            // accepts one and 401s the rest (TF-607).
            try {
              await withTokenRefreshLock(
                async () => {
                  const timeoutPromise = new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('Token refresh timeout')), 5000)
                  );

                  const tokens = await Promise.race([
                    AuthService.refreshToken({ refresh_token: refreshToken }),
                    timeoutPromise
                  ]) as any;

                  await applyTokens(tokens.access_token, tokens.refresh_token);
                },
                async () => {
                  // Another tab rotated while we queued — its fresh pair is
                  // already in localStorage, so use that instead of burning it.
                  const access = localStorage.getItem(ACCESS_TOKEN_KEY);
                  const refresh = localStorage.getItem(REFRESH_TOKEN_KEY);
                  if (!access || !refresh) {
                    throw new Error('Tokens disappeared while waiting for the refresh lock');
                  }
                  await applyTokens(access, refresh);
                },
                'mount',
              );
            } catch (refreshError) {
              console.error('[AuthContext] Token refresh failed:', refreshError);
              cancelRefreshTimer();

              // applyTokens() persists a rotated/adopted pair before fetching
              // the profile, so a failure here (e.g. the profile fetch timed
              // out) may still have left a live, freshly issued pair in
              // localStorage. Wiping it out unconditionally would strand
              // every other tab waiting on the cross-tab lock with a refresh
              // token the backend already invalidated. Only clear the
              // pre-refresh pair this mount attempt actually started with.
              if (localStorage.getItem(ACCESS_TOKEN_KEY) === accessToken) {
                localStorage.removeItem(ACCESS_TOKEN_KEY);
                localStorage.removeItem(REFRESH_TOKEN_KEY);
                localStorage.removeItem(USER_KEY);
              }

              setState({
                user: null,
                accessToken: null,
                refreshToken: null,
                isAuthenticated: false,
                isLoading: false,
                error: null,
              });
            }
          }
        } else {
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('[AuthContext] Failed to load auth state:', error);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    loadAuthState();
  }, [cancelRefreshTimer]);

  /**
   * Login with email and password
   */
  const login = useCallback(async (email: string, password: string) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const tokens = await AuthService.login({ email, password });
      const user = await AuthService.getProfile(tokens.access_token);

      if (user.preferred_language) {
        await i18n.changeLanguage(user.preferred_language).catch((e: unknown) =>
          console.error('[AuthContext] Failed to apply preferred language:', e)
        );
      }

      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      setState({
        user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      scheduleTokenRefresh(tokens.access_token);
    } catch (error) {
      console.error('[AuthContext] Login error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Login failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, [scheduleTokenRefresh]);

  /**
   * Login with pre-existing tokens (used by OAuth callback)
   */
  const loginWithTokens = useCallback(async (accessToken: string, refreshToken: string) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const user = await AuthService.getProfile(accessToken);

      if (user.preferred_language) {
        await i18n.changeLanguage(user.preferred_language).catch((e: unknown) =>
          console.error('[AuthContext] Failed to apply preferred language:', e)
        );
      }

      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      setState({
        user,
        accessToken,
        refreshToken,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      scheduleTokenRefresh(accessToken);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Token login failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, [scheduleTokenRefresh]);

  /**
   * Register new user
   */
  const register = useCallback(async (data: RegisterRequest) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const tokens = await AuthService.register(data);
      const user = await AuthService.getProfile(tokens.access_token);

      if (user.preferred_language) {
        await i18n.changeLanguage(user.preferred_language).catch((e: unknown) =>
          console.error('[AuthContext] Failed to apply preferred language:', e)
        );
      }

      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      setState({
        user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      scheduleTokenRefresh(tokens.access_token);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Registration failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, [scheduleTokenRefresh]);

  /**
   * Logout
   */
  const logout = useCallback(async () => {
    // Cancel before awaiting so the proactive timer cannot fire a refresh
    // against the session we are about to revoke.
    cancelRefreshTimer();
    try {
      if (state.accessToken) {
        await AuthService.logout(state.accessToken);
      }
    } catch (error) {
      console.error('[AuthContext] Logout error:', error);
    } finally {
      // Broadcast *before* tearing down locally: this is the one path that
      // actually revoked every session on the backend, so it is the one
      // path other tabs' storage listener should treat as proof the session
      // is dead and follow (TF-607). clearLocalSession() on its own — e.g.
      // from a failed refresh — must not trigger the same cascade.
      localStorage.setItem(LOGOUT_BROADCAST_KEY, String(Date.now()));
      clearLocalSession();
    }
  }, [state.accessToken, cancelRefreshTimer, clearLocalSession]);

  /**
   * Refresh access token.
   *
   * Do not call this directly from components — go through
   * executeTokenRefresh() (registered below as the tokenRefreshCallback),
   * which deduplicates concurrent callers within this tab and serializes
   * across tabs via the cross-tab lock. Calling this function on its own
   * bypasses both.
   */
  const refreshAccessToken = useCallback(async () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) {
      clearLocalSession();
      throw new Error('No refresh token available');
    }
    const accessTokenBefore = localStorage.getItem(ACCESS_TOKEN_KEY);
    try {
      const tokens = await AuthService.refreshToken({ refresh_token: refreshToken });
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      setState(prev => ({
        ...prev,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      }));
      scheduleTokenRefreshRef.current(tokens.access_token);
    } catch (error) {
      console.error('[AuthContext] Token refresh failed:', error);

      // Another tab may have rotated successfully while our request was in
      // flight, which kills the token we sent. Web Locks normally serialize
      // us so this cannot happen; without them (Safari < 15.4) it can. A
      // changed access token means the session is alive — adopt it instead
      // of tearing down a perfectly good session.
      if (localStorage.getItem(ACCESS_TOKEN_KEY) !== accessTokenBefore && adoptStoredTokens()) {
        return;
      }

      clearLocalSession();
      throw error;
    }
  }, [clearLocalSession, adoptStoredTokens]);

  useEffect(() => {
    refreshAccessTokenRef.current = refreshAccessToken;
  }, [refreshAccessToken]);

  useEffect(() => {
    scheduleTokenRefreshRef.current = scheduleTokenRefresh;
  }, [scheduleTokenRefresh]);

  useEffect(() => {
    setTokenRefreshCallback(refreshAccessToken);
    // The api client reaches for this only on unrecoverable auth failures, so
    // it gets the local teardown — not `logout`, which revokes every session
    // of the user on the backend (TF-607).
    setLogoutCallback(async () => clearLocalSession());
    // adoptStoredTokens() returns a boolean; the callback contract requires
    // throwing on failure instead (mirrors the rotate callback next to it),
    // so a lost adoption cannot look like a successful refresh to any caller
    // of executeTokenRefresh.
    setAdoptStoredTokensCallback(async () => {
      if (!adoptStoredTokens()) {
        throw new Error('No stored tokens to adopt');
      }
    });
    setupFetchInterceptor();
  }, [refreshAccessToken, clearLocalSession, adoptStoredTokens]);

  /**
   * Follow token changes made by other tabs.
   *
   * The backend rotates the refresh token on every use, so a tab holding a
   * stale copy would kill the session for everyone. The `storage` event fires
   * only in the tabs that did not write, which is exactly who needs to catch
   * up (TF-607).
   *
   * A bare token removal is deliberately treated as weaker evidence than a
   * broadcast logout or a full clear: another tab's own refresh attempt can
   * fail for reasons that say nothing about whether the backend session is
   * dead (a network blip, a lost race, a timeout), and cascading a logout
   * from that would just recreate — via localStorage instead of the backend
   * — the exact multi-tab logout this fix exists to prevent. Only an
   * explicit LOGOUT_BROADCAST_KEY write or a wholesale clear count as proof
   * the session is actually gone.
   */
  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      const isFullClear = event.key === null;
      const isLogoutBroadcast = event.key === LOGOUT_BROADCAST_KEY;
      const isTokenChange = event.key === ACCESS_TOKEN_KEY;

      if (!isFullClear && !isLogoutBroadcast && !isTokenChange) return;
      // A tab without a session has nothing to sync; adopting tokens here
      // would leave it with credentials but no loaded user.
      if (!isAuthenticatedRef.current) return;

      if (isFullClear || isLogoutBroadcast) {
        clearLocalSession();
        return;
      }

      if (!adoptStoredTokens()) {
        // The token vanished without a logout broadcast: another tab's own
        // refresh attempt failed and tore down *its* local session, which is
        // not proof this tab's session is dead too. This tab's own tokens
        // still worked the last time it checked, so keep running and write
        // them back rather than cascading a logout from what may be a
        // one-tab hiccup.
        const { accessToken, refreshToken } = currentTokensRef.current;
        if (accessToken && refreshToken) {
          localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
          localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        }
      }
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [adoptStoredTokens, clearLocalSession]);

  useEffect(() => {
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, []);

  /**
   * Update user profile
   */
  const updateProfile = useCallback(async (data: UpdateProfileRequest) => {
    try {
      if (!state.accessToken) {
        throw new Error('Not authenticated');
      }

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const user = await AuthService.updateProfile(state.accessToken, data);

      localStorage.setItem(USER_KEY, JSON.stringify(user));

      setState(prev => ({
        ...prev,
        user,
        isLoading: false,
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Profile update failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, [state.accessToken]);

  /**
   * Set password for OAuth-only users
   */
  const setPassword = useCallback(async (password: string) => {
    try {
      if (!state.accessToken) {
        throw new Error('Not authenticated');
      }

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      await AuthService.setPassword(state.accessToken, password);

      setState(prev => ({
        ...prev,
        isLoading: false,
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to set password';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, [state.accessToken]);

  /**
   * Change password
   */
  const changePassword = useCallback(async (data: ChangePasswordRequest) => {
    try {
      if (!state.accessToken) {
        throw new Error('Not authenticated');
      }

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      await AuthService.changePassword(state.accessToken, data);

      setState(prev => ({
        ...prev,
        isLoading: false,
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Password change failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, [state.accessToken]);

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
    loginWithTokens,
    register,
    logout,
    refreshAccessToken,
    updateProfile,
    setPassword,
    changePassword,
    clearError,
    hasPermission,
    hasRole,
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
