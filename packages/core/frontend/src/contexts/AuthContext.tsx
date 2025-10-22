/**
 * Authentication Context
 * Global auth state management with React Context
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  AuthState,
  AuthContextType,
  User,
  UserRole,
  RegisterRequest,
  UpdateProfileRequest,
  ChangePasswordRequest,
  SetPasswordRequest
} from '../types/auth';
import AuthService from '../services/AuthService';

// ============================================================================
// Context Creation
// ============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================================================
// Local Storage Keys
// ============================================================================

const ACCESS_TOKEN_KEY = 'examcraft_access_token';
const REFRESH_TOKEN_KEY = 'examcraft_refresh_token';
const USER_KEY = 'examcraft_user';

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

  // Debug logging for state changes
  useEffect(() => {
    console.log('[AuthContext] State changed:', {
      isAuthenticated: state.isAuthenticated,
      isLoading: state.isLoading,
      hasUser: !!state.user,
      hasToken: !!state.accessToken,
    });
  }, [state.isAuthenticated, state.isLoading, state.user, state.accessToken]);

  /**
   * Load auth state from localStorage on mount
   */
  useEffect(() => {
    const loadAuthState = async () => {
      try {
        console.log('[AuthContext] Loading auth state from localStorage...');
        const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

        console.log('[AuthContext] Tokens present:', !!accessToken, !!refreshToken);

        if (accessToken && refreshToken) {
          // Always fetch fresh profile instead of relying on cached user
          try {
            console.log('[AuthContext] Verifying token with getProfile...');
            const profile = await AuthService.getProfile(accessToken);
            console.log('[AuthContext] Token valid! Setting authenticated state for:', profile.email);

            // Update localStorage with fresh user data
            localStorage.setItem(USER_KEY, JSON.stringify(profile));

            setState({
              user: profile,
              accessToken,
              refreshToken,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
          } catch (error) {
            console.error('[AuthContext] Token verification failed:', error);
            // Token expired, try to refresh
            try {
              console.log('[AuthContext] Attempting token refresh...');
              const tokens = await AuthService.refreshToken({ refresh_token: refreshToken });
              const profile = await AuthService.getProfile(tokens.access_token);

              localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
              localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
              localStorage.setItem(USER_KEY, JSON.stringify(profile));

              console.log('[AuthContext] Token refreshed successfully for:', profile.email);
              setState({
                user: profile,
                accessToken: tokens.access_token,
                refreshToken: tokens.refresh_token,
                isAuthenticated: true,
                isLoading: false,
                error: null,
              });
            } catch (refreshError) {
              console.error('[AuthContext] Token refresh failed:', refreshError);
              // Refresh failed, clear auth state
              localStorage.removeItem(ACCESS_TOKEN_KEY);
              localStorage.removeItem(REFRESH_TOKEN_KEY);
              localStorage.removeItem(USER_KEY);

              console.log('[AuthContext] Cleared auth state due to refresh failure');
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
          console.log('[AuthContext] No tokens found in localStorage, setting unauthenticated state');
          setState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('[AuthContext] Failed to load auth state:', error);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    loadAuthState();
  }, []);

  /**
   * Login with email and password
   */
  const login = useCallback(async (email: string, password: string) => {
    try {
      console.log('[AuthContext] login called, setting isLoading: true');
      setState(prev => {
        console.log('[AuthContext] Previous state:', prev);
        return { ...prev, isLoading: true, error: null };
      });

      console.log('[AuthContext] Calling AuthService.login...');
      const tokens = await AuthService.login({ email, password });
      console.log('[AuthContext] Login successful, fetching profile...');
      const user = await AuthService.getProfile(tokens.access_token);

      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));

      console.log('[AuthContext] Setting authenticated state');
      setState({
        user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
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
  }, []);

  /**
   * Register new user
   */
  const register = useCallback(async (data: RegisterRequest) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      const tokens = await AuthService.register(data);
      const user = await AuthService.getProfile(tokens.access_token);
      
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
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Registration failed';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, []);

  /**
   * Logout
   */
  const logout = useCallback(async () => {
    console.log('[AuthContext] Logout called');
    try {
      if (state.accessToken) {
        await AuthService.logout(state.accessToken);
      }
    } catch (error) {
      console.error('[AuthContext] Logout error:', error);
    } finally {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);

      console.log('[AuthContext] Cleared auth state and localStorage');
      setState({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  }, [state.accessToken]);

  /**
   * Refresh access token
   */
  const refreshAccessToken = useCallback(async () => {
    try {
      if (!state.refreshToken) {
        throw new Error('No refresh token available');
      }
      
      const tokens = await AuthService.refreshToken({ refresh_token: state.refreshToken });
      const user = await AuthService.getProfile(tokens.access_token);
      
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      
      setState(prev => ({
        ...prev,
        user,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      }));
    } catch (error) {
      console.error('Token refresh failed:', error);
      await logout();
      throw error;
    }
  }, [state.refreshToken, logout]);

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
   */
  const hasPermission = useCallback((permission: string): boolean => {
    if (!state.user) return false;
    if (state.user.is_superuser) return true;

    // Guard against undefined roles or permissions
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

