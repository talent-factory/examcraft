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

  static async create(payload: OrgUnitCreate): Promise<OrgUnitOut> {
    return postJson<OrgUnitOut>(ROOT, payload);
  }

  static async update(orgUnitId: number, payload: OrgUnitUpdate): Promise<OrgUnitOut> {
    return patchJson<OrgUnitOut>(`${ROOT}/${orgUnitId}`, payload);
  }

  static async remove(orgUnitId: number): Promise<void> {
    return deleteVoid(`${ROOT}/${orgUnitId}`);
  }
}
