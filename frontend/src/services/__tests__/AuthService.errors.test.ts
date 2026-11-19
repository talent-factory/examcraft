import AuthService from '../AuthService';

/**
 * Error-path wiring for `AuthService` (TF-772 PR 3, reduced in EXAMCRAFT-126).
 *
 * The mechanics of reading `error_code` off a response live in
 * `errors/__tests__/appErrorFromResponse.test.ts`; what is pinned HERE is the
 * per-endpoint mapping — that each method passes the fallback code its own
 * endpoint needs, and that a specific backend code beats that fallback.
 *
 * The second half is the half that would silently regress. `core/backend/api/
 * auth.py` answers a failed login with five distinct codes (locked, disabled,
 * pending, invalid credentials, service unavailable) and has done since
 * TF-670, in the user's language. Collapsing all five into `auth_login_failed`
 * would still look right in a diff and would still show the user a sentence —
 * just no longer the one that says which of the five happened.
 */

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

function failWith(body: unknown, status = 500): void {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: 'Error',
    json: async () => body,
  } as Response);
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('AuthService — Fallback-Codes je Endpunkt', () => {
  const CASES: Array<[string, () => Promise<unknown>, string]> = [
    ['logout', () => AuthService.logout(), 'auth_logout_failed'],
    ['getProfile', () => AuthService.getProfile(), 'auth_profile_load_failed'],
    ['updateProfile', () => AuthService.updateProfile({}), 'auth_profile_update_failed'],
  ];

  for (const [name, call, code] of CASES) {
    it(`${name} → ${code}`, async () => {
      // No error_code in the body: the pre-ADR-0005 shape, and still what a
      // framework 500 or a proxy error page produces.
      failWith({ detail: 'Internal Server Error' });
      await expect(call()).rejects.toMatchObject({ code });
    });
  }

  it('logout wirft bei 401 nicht — die Session ist dann ohnehin weg', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'Token expired' }),
    } as Response);

    await expect(AuthService.logout()).resolves.toBeUndefined();
  });
});

describe('AuthService — spezifischer Backend-Code schlägt den Fallback', () => {
  it('reicht auth_email_taken durch statt auth_profile_update_failed', async () => {
    failWith({ detail: 'E-Mail-Adresse ist bereits registriert', error_code: 'auth_email_taken' }, 409);

    await expect(AuthService.updateProfile({ email: 'a@b.ch' })).rejects.toMatchObject({
      code: 'auth_email_taken',
    });
  });

  it('behält den rohen detail-Text für das Log, ohne ihn zur Meldung zu machen', async () => {
    // `detail` must survive onto the AppError (translateError logs it) while
    // never becoming the rendered message (TF-671).
    failWith({ detail: 'Token ungültig', error_code: 'auth_token_invalid' }, 401);

    await expect(AuthService.getProfile()).rejects.toMatchObject({
      code: 'auth_token_invalid',
      detail: 'Token ungültig',
    });
  });
});

describe('AuthService — 422 ohne error_code', () => {
  it('fällt auf den Endpunkt-Code zurück statt auf Pydantics englischen Text', async () => {
    failWith(
      { detail: [{ msg: 'Value error, String should have at least 8 characters' }] },
      422,
    );

    await expect(AuthService.updateProfile({})).rejects.toMatchObject({
      code: 'auth_profile_update_failed',
    });
  });
});
