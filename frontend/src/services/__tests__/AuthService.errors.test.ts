import AuthService from '../AuthService';

/**
 * Error-path wiring for `AuthService` (TF-772 PR 3).
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
    ['register', () => AuthService.register({} as never), 'auth_registration_failed'],
    ['login', () => AuthService.login({} as never), 'auth_login_failed'],
    ['logout', () => AuthService.logout('token'), 'auth_logout_failed'],
    ['refreshToken', () => AuthService.refreshToken({} as never), 'auth_token_refresh_failed'],
    ['getProfile', () => AuthService.getProfile('token'), 'auth_profile_load_failed'],
    ['updateProfile', () => AuthService.updateProfile('token', {}), 'auth_profile_update_failed'],
    ['setPassword', () => AuthService.setPassword('token', 'pw'), 'auth_password_set_failed'],
    ['changePassword', () => AuthService.changePassword('token', {} as never), 'auth_password_change_failed'],
    ['requestPasswordReset', () => AuthService.requestPasswordReset({} as never), 'auth_password_reset_request_failed'],
    ['confirmPasswordReset', () => AuthService.confirmPasswordReset({} as never), 'auth_password_reset_failed'],
    ['getOAuthLoginUrl', () => AuthService.getOAuthLoginUrl('google'), 'auth_oauth_url_failed'],
    ['exchangeOAuthCode', () => AuthService.exchangeOAuthCode('code'), 'auth_oauth_exchange_failed'],
  ];

  for (const [name, call, code] of CASES) {
    it(`${name} → ${code}`, async () => {
      // No error_code in the body: the pre-ADR-0005 shape, and still what a
      // framework 500 or a proxy error page produces.
      failWith({ detail: 'Internal Server Error' });
      await expect(call()).rejects.toMatchObject({ code });
    });
  }

  it('logout wirft bei 401 nicht — das Token ist dann ohnehin weg', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'Token expired' }),
    } as Response);

    await expect(AuthService.logout('token')).resolves.toBeUndefined();
  });
});

describe('AuthService — spezifischer Backend-Code schlägt den Fallback', () => {
  it('reicht auth_account_locked durch statt auth_login_failed', async () => {
    failWith(
      { detail: 'Konto gesperrt. Bitte versuch es später erneut', error_code: 'auth_account_locked' },
      403,
    );

    await expect(AuthService.login({} as never)).rejects.toMatchObject({
      code: 'auth_account_locked',
      status: 403,
    });
  });

  it('reicht auth_email_taken durch statt auth_registration_failed', async () => {
    failWith({ detail: 'E-Mail-Adresse ist bereits registriert', error_code: 'auth_email_taken' }, 409);

    await expect(AuthService.register({} as never)).rejects.toMatchObject({
      code: 'auth_email_taken',
    });
  });

  it('reicht auth_password_incorrect durch statt auth_password_change_failed', async () => {
    failWith({ detail: 'Aktuelles Passwort ist falsch', error_code: 'auth_password_incorrect' }, 400);

    await expect(AuthService.changePassword('token', {} as never)).rejects.toMatchObject({
      code: 'auth_password_incorrect',
    });
  });

  it('reicht auth_oauth_code_invalid durch statt auth_oauth_exchange_failed', async () => {
    failWith({ detail: 'Ungültiger OAuth-Code', error_code: 'auth_oauth_code_invalid' }, 400);

    await expect(AuthService.exchangeOAuthCode('code')).rejects.toMatchObject({
      code: 'auth_oauth_code_invalid',
    });
  });

  it('behält den rohen detail-Text für das Log, ohne ihn zur Meldung zu machen', async () => {
    // `detail` must survive onto the AppError (translateError logs it) while
    // never becoming the rendered message — that split is the whole point of
    // TF-671's AppError, and a service that dropped `detail` would make the
    // console trail useless.
    failWith({ detail: 'Ungültige E-Mail oder Passwort', error_code: 'auth_invalid_credentials' }, 401);

    await expect(AuthService.login({} as never)).rejects.toMatchObject({
      code: 'auth_invalid_credentials',
      detail: 'Ungültige E-Mail oder Passwort',
    });
  });
});

describe('AuthService — 422 ohne error_code', () => {
  it('fällt auf den Endpunkt-Code zurück statt auf Pydantics englischen Text', async () => {
    // FastAPI's own 422 body is `detail: [{msg: 'String should have at least
    // 8 characters', ...}]` — an English array. The old code dug `detail[0].msg`
    // out of it and rendered it; the array is not a string, so it cannot
    // become the message any more.
    failWith(
      { detail: [{ msg: 'Value error, String should have at least 8 characters' }] },
      422,
    );

    await expect(AuthService.register({} as never)).rejects.toMatchObject({
      code: 'auth_registration_failed',
    });
  });

  it('nimmt validation_error an, sobald das Backend ihn mitschickt', async () => {
    // TF-773's framework handler will send this; until it merges, the branch
    // above is what actually happens. Registered so the specific code wins the
    // day it starts arriving, without another frontend change.
    failWith({ detail: 'Die Anfrage ist ungültig.', error_code: 'validation_error' }, 422);

    await expect(AuthService.register({} as never)).rejects.toMatchObject({
      code: 'validation_error',
    });
  });
});
