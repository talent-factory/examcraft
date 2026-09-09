import RBACService from '../RBACService';

/**
 * Error-path wiring for `RBACService` (TF-772 PR 3). Like `AdminService`, it
 * had no test file at all.
 *
 * `api/v1/rbac.py` is read-only and raises exactly five codes, so the ratio
 * here is the opposite of the other two services: nine per-endpoint fallbacks
 * carry most of the load, and the specific codes matter for the three lookups
 * that can legitimately miss (`tiers/my` on a user with no institution is the
 * one an admin actually hits).
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

describe('RBACService — Fallback-Codes je Endpunkt', () => {
  const CASES: Array<[string, () => Promise<unknown>, string]> = [
    ['listFeatures', () => RBACService.listFeatures(), 'rbac_features_load_failed'],
    ['getFeature', () => RBACService.getFeature('f1'), 'rbac_feature_load_failed'],
    ['listRoles', () => RBACService.listRoles(), 'rbac_roles_load_failed'],
    ['getRole', () => RBACService.getRole('r1'), 'rbac_role_load_failed'],
    ['listSubscriptionTiers', () => RBACService.listSubscriptionTiers(), 'rbac_tiers_load_failed'],
    ['getTierQuotas', () => RBACService.getTierQuotas('t1'), 'rbac_tier_quotas_load_failed'],
    ['getMyTier', () => RBACService.getMyTier(), 'rbac_my_tier_load_failed'],
    ['checkPermission', () => RBACService.checkPermission('rag'), 'rbac_permission_check_failed'],
    ['checkQuota', () => RBACService.checkQuota('documents'), 'rbac_quota_check_failed'],
  ];

  for (const [name, call, code] of CASES) {
    it(`${name} → ${code}`, async () => {
      failWith({ detail: 'Internal Server Error' });
      await expect(call()).rejects.toMatchObject({ code });
    });
  }
});

describe('RBACService — spezifischer Backend-Code schlägt den Fallback', () => {
  it('reicht rbac_no_institution durch statt rbac_quota_check_failed', async () => {
    failWith(
      { detail: 'Benutzer ist keiner Institution zugeordnet', error_code: 'rbac_no_institution' },
      400,
    );

    await expect(RBACService.checkQuota('documents')).rejects.toMatchObject({
      code: 'rbac_no_institution',
      status: 400,
    });
  });

  it('unterscheidet rbac_institution_not_found von rbac_tier_not_found bei tiers/my', async () => {
    // Both come from the same endpoint and mean different things: the user has
    // no institution record, versus the institution has no tier assigned.
    failWith(
      { detail: 'Institution des Benutzers nicht gefunden', error_code: 'rbac_institution_not_found' },
      404,
    );
    await expect(RBACService.getMyTier()).rejects.toMatchObject({
      code: 'rbac_institution_not_found',
    });

    failWith(
      { detail: 'Abonnementtarif nicht gefunden', error_code: 'rbac_tier_not_found' },
      404,
    );
    await expect(RBACService.getMyTier()).rejects.toMatchObject({ code: 'rbac_tier_not_found' });
  });

  it('reicht rbac_feature_not_found durch statt rbac_feature_load_failed', async () => {
    failWith({ detail: 'Feature nicht gefunden', error_code: 'rbac_feature_not_found' }, 404);

    await expect(RBACService.getFeature('nope')).rejects.toMatchObject({
      code: 'rbac_feature_not_found',
    });
  });
});

describe('RBACService — Oberfläche', () => {
  it('bietet keine schreibenden Rollen-Methoden mehr an', () => {
    // createRole (POST /api/v1/rbac/roles) and updateRoleFeatures
    // (PUT /api/v1/rbac/roles/{id}/features) addressed endpoints that
    // api/v1/rbac.py does not define — the router is GET-only — and nothing in
    // any of the three frontend tiers called them. Deleted rather than given
    // two fallback codes and eight locale entries for requests that could only
    // ever answer 405.
    expect((RBACService as unknown as Record<string, unknown>).createRole).toBeUndefined();
    expect((RBACService as unknown as Record<string, unknown>).updateRoleFeatures).toBeUndefined();
  });
});
