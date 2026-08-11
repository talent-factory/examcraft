import { getJson, postJson, patchJson, deleteVoid } from './httpClient';
import {
  OrgUnitListOut,
  OrgUnitOut,
  OrgUnitCreate,
  OrgUnitUpdate,
} from '../types/orgUnit';

const ROOT = '/api/v1/org-units';

export class OrgUnitsService {
  static async list(): Promise<OrgUnitListOut> {
    return getJson<OrgUnitListOut>(ROOT);
  }

  /**
   * OrgUnits the current user is a member of (TF-620). Unlike `list()`, this
   * is not gated by `manage_org_units` — any authenticated user needs it to
   * pick a target OrgUnit for the `team` document visibility tier.
   */
  static async mine(): Promise<OrgUnitListOut> {
    return getJson<OrgUnitListOut>(`${ROOT}/mine`);
  }

  static async create(payload: OrgUnitCreate): Promise<OrgUnitOut> {
    return postJson<OrgUnitOut>(ROOT, payload);
  }

  static async update(orgUnitId: number, payload: OrgUnitUpdate): Promise<OrgUnitOut> {
    return patchJson<OrgUnitOut>(`${ROOT}/${orgUnitId}`, payload);
  }

  static async remove(orgUnitId: number): Promise<void> {
    return deleteVoid(`${ROOT}/${orgUnitId}`);
  }

  static async addMember(
    orgUnitId: number,
    userId: number,
    role?: string | null,
  ): Promise<{ user_id: number; org_unit_id: number }> {
    return postJson(`${ROOT}/${orgUnitId}/members`, { user_id: userId, role: role ?? null });
  }

  static async removeMember(orgUnitId: number, userId: number): Promise<void> {
    return deleteVoid(`${ROOT}/${orgUnitId}/members/${userId}`);
  }
}
