import AdminService from '../AdminService';

/**
 * Error-path wiring for `AdminService` (TF-772 PR 3). `AdminService` had no
 * test file at all, so the fourteen throw sites this ticket rewrote had no
 * coverage.
 *
 * The specific-code half matters more here than anywhere else in the package.
 * `core/backend/api/admin.py` distinguishes eleven refusal reasons that all
 * arrive as the same HTTP 403/409 — "you cannot deactivate your own account",
 * "user is already in this institution", "the last role cannot be removed",
 * "self-impersonation is not possible" — and an admin who is told only
 * "action failed" has to guess which rule they hit.
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
  localStorage.setItem('examcraft_access_token', 'test-token');
});

describe('AdminService — Fallback-Codes je Endpunkt', () => {
  const CASES: Array<[string, () => Promise<unknown>, string]> = [
    ['listUsers', () => AdminService.listUsers(), 'admin_users_load_failed'],
    ['getUser', () => AdminService.getUser(1), 'admin_user_load_failed'],
    ['updateUser', () => AdminService.updateUser(1, {}), 'admin_user_update_failed'],
    ['updateUserStatus', () => AdminService.updateUserStatus(1, 'active' as never), 'admin_user_status_update_failed'],
    ['impersonateUser', () => AdminService.impersonateUser(1, 'reason', 'pw'), 'impersonation_start_failed'],
    ['endImpersonation', () => AdminService.endImpersonation(), 'impersonation_end_failed'],
    ['previewTransfer', () => AdminService.previewTransfer(1, 2), 'admin_transfer_preview_failed'],
    ['transferUser', () => AdminService.transferUser(1, { target_institution_id: 2 }), 'admin_transfer_failed'],
    ['assignRole', () => AdminService.assignRole(1, 2), 'admin_role_assign_failed'],
    ['removeRole', () => AdminService.removeRole(1, 2), 'admin_role_remove_failed'],
    ['listRoles', () => AdminService.listRoles(), 'admin_roles_load_failed'],
    ['listInstitutions', () => AdminService.listInstitutions(), 'admin_institutions_load_failed'],
    ['updateInstitution', () => AdminService.updateInstitution(1, { name: 'X' }), 'admin_institution_update_failed'],
    ['createInstitution', () => AdminService.createInstitution({ name: 'X', domain: 'x.ch' }), 'admin_institution_create_failed'],
  ];

  for (const [name, call, code] of CASES) {
    it(`${name} → ${code}`, async () => {
      failWith({ detail: 'Internal Server Error' });
      await expect(call()).rejects.toMatchObject({ code });
    });
  }

  it('endImpersonation wirft bei 204 nicht', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 204,
      statusText: 'No Content',
      json: async () => ({}),
    } as Response);

    await expect(AdminService.endImpersonation()).resolves.toBeUndefined();
  });

  it('überlebt eine Antwort ohne JSON-Body', async () => {
    // The two institution endpoints already parsed defensively (a gateway 502
    // has no JSON); appErrorFromResponse now does that for every endpoint, so
    // a bodyless failure still produces the operation's code instead of a
    // "Unexpected end of JSON input" masking it.
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
      json: async () => {
        throw new SyntaxError('Unexpected end of JSON input');
      },
    } as unknown as Response);

    await expect(AdminService.listUsers()).rejects.toMatchObject({
      code: 'admin_users_load_failed',
      status: 502,
    });
  });
});

describe('AdminService — spezifischer Backend-Code schlägt den Fallback', () => {
  it('reicht admin_cannot_deactivate_self durch statt admin_user_status_update_failed', async () => {
    failWith(
      {
        detail: 'Du kannst dein eigenes Konto nicht deaktivieren',
        error_code: 'admin_cannot_deactivate_self',
      },
      400,
    );

    await expect(AdminService.updateUserStatus(1, 'inactive' as never)).rejects.toMatchObject({
      code: 'admin_cannot_deactivate_self',
      status: 400,
    });
  });

  it('reicht admin_cannot_remove_last_role durch statt admin_role_remove_failed', async () => {
    failWith(
      { detail: 'Letzte Rolle kann nicht entfernt werden', error_code: 'admin_cannot_remove_last_role' },
      409,
    );

    await expect(AdminService.removeRole(1, 2)).rejects.toMatchObject({
      code: 'admin_cannot_remove_last_role',
    });
  });

  it('reicht admin_transfer_same_institution durch statt admin_transfer_failed', async () => {
    failWith(
      { detail: 'Benutzer ist bereits in dieser Institution', error_code: 'admin_transfer_same_institution' },
      409,
    );

    await expect(
      AdminService.transferUser(1, { target_institution_id: 2 }),
    ).rejects.toMatchObject({ code: 'admin_transfer_same_institution' });
  });

  it('nimmt die impersonation_*-Codes an, die nur der Impersonation-Endpunkt kennt', async () => {
    failWith(
      { detail: 'Selbst-Impersonation ist nicht möglich', error_code: 'impersonation_self_not_allowed' },
      400,
    );

    await expect(AdminService.impersonateUser(1, 'reason', 'pw')).rejects.toMatchObject({
      code: 'impersonation_self_not_allowed',
    });
  });

  it('nimmt auch die beiden auth_*-Codes an, die die Impersonation auslösen kann', async () => {
    // POST /users/{id}/impersonate re-checks the admin's own password, so it
    // answers with auth_password_incorrect and auth_account_locked — codes
    // that belong to auth.ts but are reachable through this service.
    failWith(
      { detail: 'Aktuelles Passwort ist falsch', error_code: 'auth_password_incorrect' },
      403,
    );

    await expect(AdminService.impersonateUser(1, 'reason', 'wrong')).rejects.toMatchObject({
      code: 'auth_password_incorrect',
    });
  });
});
