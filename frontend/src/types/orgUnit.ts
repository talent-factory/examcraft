export interface OrgUnitOut {
  id: number;
  parent_org_unit_id: number | null;
  unit_type: string;
  name: string;
  descendant_count: number;
  // Granted Role (TF-637): the Role this OrgUnit grants to its *direct*
  // members. Distinct from OrgUnitMember.role below, which is the
  // Membership Label free-text field and never carries permissions — see
  // CONTEXT.md.
  role_id: number | null;
  role_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrgUnitListOut {
  items: OrgUnitOut[];
}

export interface OrgUnitCreate {
  unit_type: string;
  name: string;
  parent_org_unit_id: number | null;
  role_id?: number | null;
}

export interface OrgUnitUpdate {
  name?: string;
  parent_org_unit_id?: number | null;
  move_to_root?: boolean;
  role_id?: number | null;
}

export interface OrgUnitMember {
  org_unit_id: number;
  name: string;
  unit_type: string;
  parent_org_unit_id: number | null;
  role: string | null;
}
