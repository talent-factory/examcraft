/**
 * Roles Service
 * Service for managing roles and permissions via the admin API
 */

import { getJson, postJson, patchJson, deleteVoid } from './httpClient';
import { PermissionOut, RoleCreate, RoleOut, RoleUpdate } from '../types/role';

const ROOT = '/api/admin/roles';

export class RolesService {
  /**
   * List all roles
   */
  static async list(): Promise<RoleOut[]> {
    return getJson<RoleOut[]>(ROOT);
  }

  /**
   * List all available permissions
   */
  static async listPermissions(): Promise<PermissionOut[]> {
    return getJson<PermissionOut[]>('/api/admin/permissions');
  }

  /**
   * Create a new role
   */
  static async create(payload: RoleCreate): Promise<RoleOut> {
    return postJson<RoleOut>(ROOT, payload);
  }

  /**
   * Update an existing role
   */
  static async update(id: number, payload: RoleUpdate): Promise<RoleOut> {
    return patchJson<RoleOut>(`${ROOT}/${id}`, payload);
  }

  /**
   * Remove a role
   */
  static async remove(id: number): Promise<void> {
    return deleteVoid(`${ROOT}/${id}`);
  }
}
