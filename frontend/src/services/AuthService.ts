/**
 * Authentication Service
 *
 * EXAMCRAFT-126: Die Anmeldung läuft als OIDC-BFF über das Backend
 * (`/api/v1/auth/login`); der Browser hält nur ein httpOnly-Session-Cookie.
 * Hier bleiben Profil und Logout. Alle Aufrufe senden das Cookie über
 * `credentials: 'include'`.
 */

import { UpdateProfileRequest, UserResponse } from '../types/auth';
import { appErrorFromResponse } from '../errors';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class AuthService {
  /**
   * URL, die den Login-Flow startet (Weiterleitung des ganzen Fensters).
   * `reauth` erzwingt eine frische Anmeldung beim IdP (Step-up), `returnTo`
   * is the relative in-app path the callback redirects to afterwards.
   */
  getLoginUrl(options: { reauth?: boolean; returnTo?: string } = {}): string {
    const params = new URLSearchParams();
    if (options.reauth) params.set('reauth', 'true');
    // The backend re-validates `return_to` (relative in-app paths only).
    if (options.returnTo) params.set('return_to', options.returnTo);
    const query = params.toString();
    return `${API_BASE_URL}/api/v1/auth/login${query ? `?${query}` : ''}`;
  }

  /**
   * Beendet die lokale Server-Session (die SSO-Session bei Zitadel bleibt).
   */
  async logout(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok && response.status !== 401) {
      throw await appErrorFromResponse(response, 'auth_logout_failed');
    }
  }

  /**
   * Get current user profile
   */
  async getProfile(): Promise<UserResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'GET',
      credentials: 'include',
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_profile_load_failed');
    }

    return response.json();
  }

  /**
   * Update user profile
   */
  async updateProfile(data: UpdateProfileRequest): Promise<UserResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'PATCH',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw await appErrorFromResponse(response, 'auth_profile_update_failed');
    }

    return response.json();
  }
}

const authService = new AuthService();
export default authService;
