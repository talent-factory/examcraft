/**
 * Authentication Service
 * API calls for authentication and user management
 */

import {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  RefreshTokenRequest,
  ChangePasswordRequest,
  PasswordResetRequest,
  PasswordResetConfirm,
  UpdateProfileRequest,
  UserResponse,
  OAuthLoginResponse,
  OAuthProvider
} from '../types/auth';
import { appErrorFromResponse } from '../errors';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class AuthService {
  /**
   * Register a new user
   */
  async register(data: RegisterRequest): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_registration_failed');
    }

    return response.json();
  }

  /**
   * Login with email and password
   */
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_login_failed');
    }

    return response.json();
  }

  /**
   * Logout (revoke tokens)
   */
  async logout(accessToken: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok && response.status !== 401) {
      throw await appErrorFromResponse(response, 'auth_logout_failed');
    }
  }

  /**
   * Refresh access token
   */
  async refreshToken(data: RefreshTokenRequest): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_token_refresh_failed');
    }

    return response.json();
  }

  /**
   * Get current user profile
   */
  async getProfile(accessToken: string): Promise<UserResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_profile_load_failed');
    }

    return response.json();
  }

  /**
   * Update user profile
   */
  async updateProfile(accessToken: string, data: UpdateProfileRequest): Promise<UserResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_profile_update_failed');
    }

    return response.json();
  }

  /**
   * Set password for OAuth-only users
   */
  async setPassword(accessToken: string, password: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/auth/set-password`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_password_set_failed');
    }
  }

  /**
   * Change password
   */
  async changePassword(accessToken: string, data: ChangePasswordRequest): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_password_change_failed');
    }
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(data: PasswordResetRequest): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/auth/password-reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_password_reset_request_failed');
    }
  }

  /**
   * Confirm password reset
   */
  async confirmPasswordReset(data: PasswordResetConfirm): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/auth/password-reset/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_password_reset_failed');
    }
  }

  /**
   * Get OAuth login URL
   */
  async getOAuthLoginUrl(provider: OAuthProvider): Promise<OAuthLoginResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/oauth/${provider}/login`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_oauth_url_failed');
    }

    return response.json();
  }

  /**
   * Exchange a short-lived OAuth code for tokens
   */
  async exchangeOAuthCode(code: string): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/oauth/exchange`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_oauth_exchange_failed');
    }

    return response.json();
  }
}

const authService = new AuthService();
export default authService;
