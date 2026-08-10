/**
 * Role & Permission Management Types
 * TypeScript types for Role and Permission administration
 */

// RoleOut mirrors the exact wire shape of api.admin.RoleResponse — the same
// backend resource types/auth.ts::Role also describes. Re-exported (not
// redefined) here so the two names can't drift apart again, as they briefly
// did in TF-603 (auth.ts::Role.description was non-nullable while this file
// correctly had `string | null`, matching the actual nullable backend field).
export type { Role as RoleOut } from './auth';

export interface PermissionOut {
  key: string;
  label: string;
  category: string;
}

export interface RoleCreate {
  name: string;
  display_name: string;
  description: string | null;
  permissions: string[];
}

export interface RoleUpdate {
  display_name?: string;
  description?: string | null;
  permissions?: string[];
}
