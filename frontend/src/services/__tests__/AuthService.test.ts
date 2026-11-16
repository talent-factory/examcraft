import authService from '../AuthService';
import { UserResponse, UserStatus } from '../../types/auth';

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

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

describe('AuthService (Cookie-Session, EXAMCRAFT-126)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getLoginUrl', () => {
    it('zeigt auf den Login-Flow des Backends', () => {
      expect(authService.getLoginUrl()).toBe('http://localhost:8000/api/v1/auth/login');
    });

    it('hängt reauth=true für den Step-up an', () => {
      expect(authService.getLoginUrl({ reauth: true })).toBe(
        'http://localhost:8000/api/v1/auth/login?reauth=true',
      );
    });

    it('kodiert return_to für den Rücksprung nach dem Step-up', () => {
      expect(authService.getLoginUrl({ reauth: true, returnTo: '/admin' })).toBe(
        'http://localhost:8000/api/v1/auth/login?reauth=true&return_to=%2Fadmin',
      );
    });
  });

  describe('getProfile', () => {
    it('lädt das Profil mit dem Cookie, ohne Authorization-Header', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockUserResponse } as Response);

      const result = await authService.getProfile();

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/me', {
        method: 'GET',
        credentials: 'include',
      });
      expect(result).toEqual(mockUserResponse);
    });

    it('wirft einen AppError mit Status bei 401', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ error_code: 'auth_token_invalid' }),
      } as Response);

      await expect(authService.getProfile()).rejects.toMatchObject({
        code: 'auth_token_invalid',
        status: 401,
      });
    });
  });

  describe('updateProfile', () => {
    it('sendet PATCH mit Cookie und JSON-Body', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockUserResponse } as Response);

      await authService.updateProfile({ first_name: 'Neu' });

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/auth/me', {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ first_name: 'Neu' }),
      });
    });
  });

  describe('logout', () => {
    it('ruft POST /api/v1/auth/logout mit Cookie auf', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 } as Response);

      await authService.logout();

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    });

    it('behandelt 401 (Session schon weg) als Erfolg', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 401 } as Response);
      await expect(authService.logout()).resolves.toBeUndefined();
    });
  });
});
