/**
 * Authentication Context
 * Global auth state management with React Context
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  AuthState,
  AuthContextType,
  UserRole,
  User,
  RegisterRequest,
  UpdateProfileRequest,
  ChangePasswordRequest,
} from '../types/auth';
import AuthService from '../services/AuthService';
import AdminService from '../services/AdminService';
import { resolveLanguageOnProfileLoad } from '../utils/languagePreference';
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
  ImpersonationEndedError,
} from '../api/tokenRefreshLock';
import {
  clearAllSessionSnapshots,
  readSessionSnapshot,
  writeSessionSnapshot,
  clearSessionSnapshot,
} from '../utils/sessionSnapshot';

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

// TF-743: sessionStorage snapshot of the admin's own tokens+profile, taken
// right before swapping the active session over to an impersonation token.
// Tab-scoped on purpose (sessionSnapshot.ts) — the admin snapshot must not
// leak to another tab or survive a full logout beyond what
// clearAllSessionSnapshots() already handles.
const IMPERSONATION_SNAPSHOT_KEY = 'impersonation.adminSession';
const IMPERSONATION_SNAPSHOT_VERSION = 1;

interface AdminSessionSnapshot {
  accessToken: string;
  refreshToken: string;
  user: User;
}

// Set on AuthState whenever a full state object is constructed for a
// non-impersonated session, so every existing call site only needs to spread
// this in instead of restating both fields by hand.
const NOT_IMPERSONATING = { isImpersonating: false, impersonationExpiresAt: null } as const;

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
    ...NOT_IMPERSONATING,
  });
  // TF-743: set by the mount effect (below) when it finds an
  // impersonation-shaped token pair on a cold reload. Deferred to a
  // separate effect — declared further down, after `restoreAdminSession`
  // — rather than called directly from the mount effect: that effect runs,
  // and its async body reaches this call, synchronously within the same
  // initial effect-flush pass as the ref-sync effect that populates
  // `restoreAdminSessionRef`, before that effect has had a chance to run.
  const [pendingReloadImpersonationRestore, setPendingReloadImpersonationRestore] = useState(false);

  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshAccessTokenRef = useRef<() => Promise<void>>(async () => {});
  const scheduleTokenRefreshRef = useRef<(token: string) => void>(() => {});
  // Forward-reference to `restoreAdminSession` (declared further down) for
  // the mount effect and `logout`, which both run/are defined earlier in
  // this component than `restoreAdminSession` itself — mirrors the same
  // pattern already used for refreshAccessTokenRef/scheduleTokenRefreshRef.
  const restoreAdminSessionRef = useRef<() => Promise<{ restored: boolean; backendEndFailed: boolean }>>(
    async () => ({ restored: false, backendEndFailed: false }),
  );
  const isAuthenticatedRef = useRef(false);
  // TF-743: mirrors state.isImpersonating for the storage listener below.
  // An impersonating tab's proactive timer alone owns its lifecycle
  // end-to-end (auto-fallback to the admin session); it must not react to
  // *other* tabs' unrelated token churn (see handleStorage below).
  const isImpersonatingRef = useRef(false);
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
    isImpersonatingRef.current = state.isImpersonating;
  }, [state.isImpersonating]);

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
      // TF-608: sessionStorage survives a user switch within the same tab;
      // rationale (shared machine) in sessionSnapshot.ts. Centralized here
      // instead of at every call site: covers explicit logout, a failed
      // refresh, AND the cross-tab logout-following (TF-607, storage listener
      // further below) alike — never forgettable when another trigger for
      // "session ended locally" is added.
      clearAllSessionSnapshots();
      setState({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        ...NOT_IMPERSONATING,
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

            // See resolveLanguageOnProfileLoad's own doc for why this — not
            // the raw account value — is what gets applied here.
            const language = resolveLanguageOnProfileLoad(profile.preferred_language);
            if (language) {
              await i18n.changeLanguage(language).catch((e: unknown) =>
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
              ...NOT_IMPERSONATING,
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

              // See resolveLanguageOnProfileLoad's own doc for why this —
              // not the raw account value — is what gets applied here.
              const language = resolveLanguageOnProfileLoad(profile.preferred_language);
              if (language) {
                await i18n.changeLanguage(language).catch((e: unknown) =>
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
                ...NOT_IMPERSONATING,
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
                // TF-608: same as for an explicit logout (see clearLocalSession).
                // An expired session in an open tab is exactly the case where
                // someone walked away and someone else sits down. Deliberately
                // inside the guard above: if the token pair still belongs to
                // another, still-logged-in tab, that tab's session isn't over
                // — its snapshots shouldn't disappear either.
                clearAllSessionSnapshots();
              }

              setState({
                user: null,
                accessToken: null,
                refreshToken: null,
                isAuthenticated: false,
                isLoading: false,
                error: null,
                ...NOT_IMPERSONATING,
              });
            }
          }
        } else if (accessToken && !refreshToken) {
          // TF-743: an access token with no refresh token means this tab
          // was mid-impersonation before this reload — impersonation
          // tokens are deliberately minted without a refresh token
          // (TF-741's hard 30-min cap, no renewal). There is no safe way
          // to resume impersonating across a reload (the token may already
          // be stale/expired, and its remaining lifetime can't be
          // recovered here), so fall back to the stashed admin session
          // instead of the previous behavior of leaving the admin fully
          // logged out on every impersonation-tab reload.
          //
          // Deferred to the effect below rather than called directly here
          // — see pendingReloadImpersonationRestore's declaration for why.
          // isLoading stays true; that effect resolves it.
          setPendingReloadImpersonationRestore(true);
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

      // See resolveLanguageOnProfileLoad's own doc for why this — not the
      // raw account value — is what gets applied here.
      const language = resolveLanguageOnProfileLoad(user.preferred_language);
      if (language) {
        await i18n.changeLanguage(language).catch((e: unknown) =>
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
        ...NOT_IMPERSONATING,
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

      // See resolveLanguageOnProfileLoad's own doc for why this — not the
      // raw account value — is what gets applied here.
      const language = resolveLanguageOnProfileLoad(user.preferred_language);
      if (language) {
        await i18n.changeLanguage(language).catch((e: unknown) =>
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
        ...NOT_IMPERSONATING,
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

      // See resolveLanguageOnProfileLoad's own doc for why this — not the
      // raw account value — is what gets applied here.
      const language = resolveLanguageOnProfileLoad(user.preferred_language);
      if (language) {
        await i18n.changeLanguage(language).catch((e: unknown) =>
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
        ...NOT_IMPERSONATING,
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
    // TF-743: logging out while impersonating must only end the
    // impersonation, mirroring the backend (auth.py's logout endpoint
    // treats logout-while-impersonating the same as POST
    // /admin/impersonate/end). A full logout here would broadcast
    // LOGOUT_BROADCAST_KEY to every tab and wipe the stashed admin
    // snapshot via clearLocalSession(), signing the admin out everywhere
    // over what the user meant as "stop impersonating".
    if (state.isImpersonating) {
      await restoreAdminSessionRef.current();
      return;
    }

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
  }, [state.accessToken, state.isImpersonating, cancelRefreshTimer, clearLocalSession]);

  /**
   * Restore the admin session stashed by `startImpersonation` (TF-743).
   *
   * Called several ways: reactively, when `refreshAccessToken` finds no
   * refresh token (an impersonation token never has one — TF-741's hard
   * 30-min cap) and a stash exists; directly, from the banner's "back to my
   * account" button, from `logout()` while impersonating, and from a
   * cold-mount reload that finds an impersonation-shaped token pair.
   * Returns `{ restored: false, backendEndFailed: false }` when there is
   * nothing to restore — either impersonation was never active in this tab,
   * or it was already restored — so every caller can treat a repeat call as
   * a harmless no-op instead of an error.
   *
   * Before touching localStorage, this best-effort tells the backend the
   * impersonation session is over (`AdminService.endImpersonation()`,
   * identified via the *current* — still impersonation — access token).
   * `backendEndFailed` reports whether that call failed so a caller like
   * the banner can surface it, but it never blocks the local restore: every
   * exit path must still land the admin back on their own session even if
   * the network call failed or the session had already expired server-side.
   *
   * The stashed pair is re-refreshed rather than reused as-is: it may have
   * sat idle for the whole impersonation window and be close to its own
   * expiry by now. If that refresh itself fails (the admin's own session
   * lapsed too), the stashed access token is restored as a last resort —
   * the next request re-authenticates normally if it's also no longer
   * valid, but the admin at least isn't logged out purely because they
   * happened to be impersonating when their own token came due.
   */
  const restoreAdminSession = useCallback(async (): Promise<{
    restored: boolean;
    backendEndFailed: boolean;
  }> => {
    const snapshot = readSessionSnapshot<AdminSessionSnapshot>(
      IMPERSONATION_SNAPSHOT_KEY,
      IMPERSONATION_SNAPSHOT_VERSION,
    );
    if (!snapshot) return { restored: false, backendEndFailed: false };

    clearSessionSnapshot(IMPERSONATION_SNAPSHOT_KEY);

    let backendEndFailed = false;
    try {
      await AdminService.endImpersonation();
    } catch (error) {
      console.error('[AuthContext] Failed to end impersonation server-side:', error);
      backendEndFailed = true;
    }

    try {
      const tokens = await AuthService.refreshToken({ refresh_token: snapshot.refreshToken });
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(snapshot.user));
      setState({
        user: snapshot.user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        ...NOT_IMPERSONATING,
      });
      scheduleTokenRefreshRef.current(tokens.access_token);
    } catch (error) {
      console.error('[AuthContext] Failed to refresh admin session on restore:', error);
      try {
        localStorage.setItem(ACCESS_TOKEN_KEY, snapshot.accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, snapshot.refreshToken);
        localStorage.setItem(USER_KEY, JSON.stringify(snapshot.user));
      } catch (storageError) {
        console.error('[AuthContext] Failed to persist fallback admin tokens:', storageError);
      }
      setState({
        user: snapshot.user,
        accessToken: snapshot.accessToken,
        refreshToken: snapshot.refreshToken,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        ...NOT_IMPERSONATING,
      });
      scheduleTokenRefreshRef.current(snapshot.accessToken);
    }
    return { restored: true, backendEndFailed };
  }, []);

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
      // TF-743: an impersonation access token carries no refresh token by
      // design. Both the proactive timer (armed like any other token, 2 min
      // before its `exp` — see REFRESH_LEAD_MS) and a reactive 401 land
      // here while impersonating; restore the stashed admin session instead
      // of tearing the tab down, so the fallback lands the admin back on
      // their own identity rather than logging them out mid-support-session.
      //
      // Throwing ImpersonationEndedError (rather than just returning) on a
      // successful restore matters: apiClient's interceptors treat a
      // resolved refresh as "retry the original request with the new
      // token", which would silently replay it under the admin's identity
      // instead of the impersonated user's. This distinct error tells them
      // to surface the original 401 instead of retrying.
      const { restored } = await restoreAdminSession();
      if (restored) throw new ImpersonationEndedError();
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
  }, [clearLocalSession, adoptStoredTokens, restoreAdminSession]);

  /**
   * Swap the active session over to an impersonation token (TF-743).
   *
   * Stashes the current (admin) session to sessionStorage — tab-scoped, see
   * IMPERSONATION_SNAPSHOT_KEY — then makes the target user's token the
   * active one, exactly like `login` does for a normal session, so the rest
   * of the app (every existing service call reads the token from
   * localStorage) transparently starts acting as the target user. No
   * refresh token is stored: TF-741 mints impersonation tokens without one
   * (hard 30-min cap, never renewed), which is also the signal
   * `refreshAccessToken` uses to route into `restoreAdminSession` later.
   *
   * Known limitation: localStorage — not sessionStorage — is what every tab
   * of this browser reads its token from at request time (TF-607's
   * cross-tab design), so another already-open tab of the same admin will
   * transiently send requests as the impersonated user too. Two of the
   * three ways that can go wrong are guarded in the storage listener below:
   * this tab silently switching to a *different* token pair a sibling tab's
   * ordinary rotation writes (`isImpersonatingRef`), and a sibling tab
   * clobbering *this* tab's impersonation token on the same signal
   * (`isImpersonationHandoff`). Not yet guarded: a sibling tab's own
   * *proactive timer* (not the storage listener) firing independently,
   * finding the shared `REFRESH_TOKEN_KEY` gone (removed by this tab's
   * `startImpersonation`), concluding *its own* session died, and calling
   * `clearLocalSession()` — which wipes this tab's impersonation token too.
   * Scoped out here as pre-existing (TF-739/TF-743's own AC only covers a
   * single active session); flagged for a follow-up.
   */
  const startImpersonation = useCallback(async (payload: { accessToken: string; expiresIn: number }) => {
    if (state.isImpersonating) {
      // Starting a second impersonation on top of an active one would
      // overwrite the stashed admin snapshot with the *current target's*
      // session, losing the actual admin's way back. Checked before the
      // "active admin session" guard below: while impersonating,
      // state.refreshToken is legitimately null by design, which would
      // otherwise be misreported as "no active admin session".
      throw new Error('Already impersonating another user; end the current impersonation first');
    }
    if (!state.accessToken || !state.refreshToken || !state.user) {
      throw new Error('Cannot start impersonation without an active admin session');
    }

    // TF-743 fix: verify the recovery snapshot actually persisted before
    // committing to the swap. sessionStorage writes fail silently on quota
    // limits or in private-browsing mode (see sessionSnapshot.ts) — without
    // this check, that failure would only surface ~28 minutes later as an
    // unexplained forced logout when the hard-cap fallback finds no way
    // back to the admin session. Refuse to start instead.
    const snapshotSaved = writeSessionSnapshot<AdminSessionSnapshot>(
      IMPERSONATION_SNAPSHOT_KEY,
      IMPERSONATION_SNAPSHOT_VERSION,
      { accessToken: state.accessToken, refreshToken: state.refreshToken, user: state.user },
    );
    if (!snapshotSaved) {
      throw new Error(
        'Impersonation session snapshot could not be saved; browser storage may be full or restricted',
      );
    }

    // Stop the admin's own proactive timer before it can fire a refresh
    // against the session we are about to leave.
    cancelRefreshTimer();

    try {
      const targetUser = await AuthService.getProfile(payload.accessToken);

      try {
        localStorage.setItem(ACCESS_TOKEN_KEY, payload.accessToken);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.setItem(USER_KEY, JSON.stringify(targetUser));
      } catch (error) {
        // A partial write here (e.g. the access token lands but the
        // refresh-token removal fails) must not be treated as a soft
        // warning: every subsequent request would read this half-written
        // state from localStorage while the setState below still claims
        // the swap fully succeeded. Rethrow so the outer catch rolls back.
        console.error('[AuthContext] Failed to persist impersonation session:', error);
        throw error;
      }

      const expiresAt = new Date(Date.now() + payload.expiresIn * 1000).toISOString();
      setState({
        user: targetUser,
        accessToken: payload.accessToken,
        refreshToken: null,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        isImpersonating: true,
        impersonationExpiresAt: expiresAt,
      });
      scheduleTokenRefreshRef.current(payload.accessToken);
    } catch (error) {
      // Roll back. localStorage may be partially written if the inner
      // write above is what failed, so explicitly restore the admin's own
      // token pair rather than assuming it is still untouched.
      try {
        localStorage.setItem(ACCESS_TOKEN_KEY, state.accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, state.refreshToken);
        localStorage.setItem(USER_KEY, JSON.stringify(state.user));
      } catch (restoreError) {
        console.error('[AuthContext] Failed to restore admin tokens after rollback:', restoreError);
      }
      clearSessionSnapshot(IMPERSONATION_SNAPSHOT_KEY);
      scheduleTokenRefreshRef.current(state.accessToken);

      // Best-effort: AdminService.impersonateUser() already created the
      // impersonation session server-side before this failure, so tell the
      // backend it was abandoned rather than leaving it open until the
      // 30-min hard cap / reaper reclaims it. localStorage still holds the
      // admin's own token at this point, so the just-issued target token
      // must be passed explicitly (see AdminService.endImpersonation).
      AdminService.endImpersonation(payload.accessToken).catch((endError) => {
        console.error('[AuthContext] Failed to close orphaned impersonation session after rollback:', endError);
      });

      throw error;
    }
  }, [state.accessToken, state.refreshToken, state.user, state.isImpersonating, cancelRefreshTimer]);

  /**
   * Public entry point for ending impersonation from the UI (the banner's
   * "back to my account" button). Tells the backend via `POST
   * /api/admin/impersonate/end` and restores local state — safe to call
   * regardless of whether the backend call succeeded, so the admin is never
   * stuck on the impersonated identity purely because the end-call itself
   * hit a network error. Returns `backendEndFailed` so the caller can
   * surface that to the admin (the local restore itself always succeeds
   * when this resolves).
   */
  const endImpersonation = useCallback(async (): Promise<{ backendEndFailed: boolean }> => {
    const { backendEndFailed } = await restoreAdminSession();
    return { backendEndFailed };
  }, [restoreAdminSession]);

  useEffect(() => {
    refreshAccessTokenRef.current = refreshAccessToken;
  }, [refreshAccessToken]);

  useEffect(() => {
    restoreAdminSessionRef.current = restoreAdminSession;
  }, [restoreAdminSession]);

  // TF-743: performs the reload-time admin-session restore the mount effect
  // deferred (see pendingReloadImpersonationRestore's declaration above).
  // Declared after `restoreAdminSession` so it can reference it directly —
  // no ref/TDZ concern here, since this effect only ever needs to run
  // *after* mount, never synchronously during the initial effect flush.
  useEffect(() => {
    if (!pendingReloadImpersonationRestore) return;
    setPendingReloadImpersonationRestore(false);
    restoreAdminSession().then(({ restored }) => {
      if (!restored) {
        setState(prev => ({ ...prev, isLoading: false }));
      }
    });
  }, [pendingReloadImpersonationRestore, restoreAdminSession]);

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

      // TF-743: this tab's own token is intrinsically shaped differently
      // while it is impersonating (no refresh token), and its proactive
      // timer already owns its entire lifecycle end-to-end (auto-fallback
      // to the admin session). Reacting to *another* tab's unrelated token
      // rotation here — adopting a foreign admin token pair, or writing
      // this tab's impersonation token back over it — would silently swap
      // the identity behind every subsequent request while the banner
      // keeps claiming to impersonate the original target.
      if (isImpersonatingRef.current) return;

      if (!adoptStoredTokens()) {
        // TF-743: an access-token change with no refresh token alongside it
        // means another tab just started (or is mid-)impersonation — never
        // the "failed rotation" case below, which always clears both keys
        // together. Writing this tab's own admin tokens back over it would
        // immediately break the impersonating tab's very next request, so
        // leave localStorage alone and let this tab's own state ride out
        // unaffected until it next needs to refresh.
        //
        // Safe default: if the storage reads below fail, assume this MIGHT
        // be a handoff and do nothing, rather than assuming it isn't and
        // clobbering whatever the other tab just wrote. Getting this wrong
        // in the other direction is exactly the bug this check exists to
        // prevent.
        let isImpersonationHandoff = true;
        try {
          isImpersonationHandoff =
            !!localStorage.getItem(ACCESS_TOKEN_KEY) && !localStorage.getItem(REFRESH_TOKEN_KEY);
        } catch (err) {
          console.error('[AuthContext] Failed to inspect storage during token-change handling:', err);
          // isImpersonationHandoff stays at its safe default (true) above.
        }
        if (isImpersonationHandoff) return;

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
