import authService from '../AuthService';
import { TokenResponse, UserResponse, UserStatus, SubscriptionTier } from '../../types/auth';

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Sample test data
const mockTokenResponse: TokenResponse = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
};

const mockUserResponse: UserResponse = {
  id: 1,
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  institution_id: 1,
  roles: [],
  status: UserStatus.ACTIVE,
  is_superuser: false,
  is_email_verified: true,
  created_at: '2025-10-01T00:00:00Z',
};

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ==========================================================================
  // exchangeOAuthCode
  // ==========================================================================

  describe('exchangeOAuthCode', () => {
    it('exchanges OAuth code for tokens successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokenResponse,
      } as Response);

      const result = await authService.exchangeOAuthCode('test-oauth-code');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/oauth/exchange',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: 'test-oauth-code' }),
        }
      );

      expect(result).toEqual(mockTokenResponse);
      expect(result.access_token).toBe('mock-access-token');
      expect(result.refresh_token).toBe('mock-refresh-token');
    });

    it('trägt den Backend-Code einer 400-Antwort', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({
          detail: 'Ungültiger OAuth-Code',
          error_code: 'auth_oauth_code_invalid',
        }),
      } as Response);

      await expect(authService.exchangeOAuthCode('expired-code'))
        .rejects.toMatchObject({ code: 'auth_oauth_code_invalid', status: 400 });
    });

    it('fällt bei 503 ohne error_code auf den Endpunkt-Code zurück', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: async () => ({ detail: 'OAuth service unavailable' }),
      } as Response);

      await expect(authService.exchangeOAuthCode('some-code'))
        .rejects.toMatchObject({ code: 'auth_oauth_exchange_failed', status: 503 });
    });

    it('nutzt den Endpunkt-Code, wenn der Body leer ist', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      } as Response);

      await expect(authService.exchangeOAuthCode('some-code'))
        .rejects.toMatchObject({ code: 'auth_oauth_exchange_failed' });
    });

    it('reicht einen Netzwerkfehler unverändert durch (kein AppError)', async () => {
      // No response, so nothing to read an error_code from. The value stays a
      // plain Error; translateError maps it to the consumer's fallback key.
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(authService.exchangeOAuthCode('some-code'))
        .rejects.toThrow('Network error');
    });
  });

  // ==========================================================================
  // updateProfile
  // ==========================================================================

  describe('updateProfile', () => {
    it('uses PATCH method (not PUT)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserResponse,
      } as Response);

      await authService.updateProfile('test-token', { first_name: 'Updated' });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/me',
        expect.objectContaining({
          method: 'PATCH',
        })
      );
    });

    it('sends correct headers and body', async () => {
      const profileData = { first_name: 'New', last_name: 'Name' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockUserResponse, ...profileData }),
      } as Response);

      await authService.updateProfile('my-access-token', profileData);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/me',
        {
          method: 'PATCH',
          headers: {
            'Authorization': 'Bearer my-access-token',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(profileData),
        }
      );
    });

    it('returns updated user response', async () => {
      const updatedUser = { ...mockUserResponse, first_name: 'Updated' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updatedUser,
      } as Response);

      const result = await authService.updateProfile('test-token', { first_name: 'Updated' });

      expect(result).toEqual(updatedUser);
      expect(result.first_name).toBe('Updated');
    });

    it('trägt den Backend-Code einer 401-Antwort', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({
          detail: 'Ungültiger oder abgelaufener Token',
          error_code: 'auth_token_invalid',
        }),
      } as Response);

      await expect(authService.updateProfile('invalid-token', { first_name: 'Test' }))
        .rejects.toMatchObject({ code: 'auth_token_invalid', status: 401 });
    });

    it('nutzt den Endpunkt-Code, wenn der Body leer ist', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      } as Response);

      await expect(authService.updateProfile('test-token', { first_name: 'Test' }))
        .rejects.toMatchObject({ code: 'auth_profile_update_failed' });
    });
  });
});
