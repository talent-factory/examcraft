import { AppErrorCode, appErrorFromApiError } from '../errors';
import { getJson, postJson, patchJson, deleteVoid } from './httpClient';
import {
  OrgUnitListOut,
  OrgUnitOut,
  OrgUnitCreate,
  OrgUnitUpdate,
} from '../types/orgUnit';

const ROOT = '/api/v1/org-units';

/**
 * Turn the `ApiError` from `httpClient` into an `AppError` for this operation
 * (TF-772).
 *
 * The conversion sits here and not in `httpClient` on purpose: that module is
 * shared with seven services outside this package, and changing the error type
 * it throws would change all of them at once. Here the blast radius is one
 * file, and the operation — which `httpClient` cannot know — is what gives the
 * code its meaning.
 */
function withCode<T>(code: AppErrorCode, call: () => Promise<T>): Promise<T> {
  return call().catch((err) => {
    throw appErrorFromApiError(err, code);
  });
}

export class OrgUnitsService {
  static async list(): Promise<OrgUnitListOut> {
    return withCode('org_units_list_failed', () => getJson<OrgUnitListOut>(ROOT));
  }

  /**
   * OrgUnits the current user is a member of (TF-620). Unlike `list()`, this
   * is not gated by `manage_org_units` — any authenticated user needs it to
   * pick a target OrgUnit for the `team` document visibility tier.
   *
   * Shares `org_units_list_failed` with `list()`: different endpoint, same
   * sentence for the reader.
   */
  static async mine(): Promise<OrgUnitListOut> {
    return withCode('org_units_list_failed', () =>
      getJson<OrgUnitListOut>(`${ROOT}/mine`),
    );
  }

  static async create(payload: OrgUnitCreate): Promise<OrgUnitOut> {
    return withCode('org_units_create_failed', () => postJson<OrgUnitOut>(ROOT, payload));
  }

  static async update(orgUnitId: number, payload: OrgUnitUpdate): Promise<OrgUnitOut> {
    return withCode('org_units_update_failed', () =>
      patchJson<OrgUnitOut>(`${ROOT}/${orgUnitId}`, payload),
    );
  }

  static async remove(orgUnitId: number): Promise<void> {
    return withCode('org_units_delete_failed', () => deleteVoid(`${ROOT}/${orgUnitId}`));
  }

  static async addMember(
    orgUnitId: number,
    userId: number,
    role?: string | null,
  ): Promise<{ user_id: number; org_unit_id: number }> {
    return withCode('org_units_add_member_failed', () =>
      postJson(`${ROOT}/${orgUnitId}/members`, { user_id: userId, role: role ?? null }),
    );
  }

  static async removeMember(orgUnitId: number, userId: number): Promise<void> {
    return withCode('org_units_remove_member_failed', () =>
      deleteVoid(`${ROOT}/${orgUnitId}/members/${userId}`),
    );
  }
}
