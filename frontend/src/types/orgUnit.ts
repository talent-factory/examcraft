export interface OrgUnitOut {
  id: number;
  parent_org_unit_id: number | null;
  unit_type: string;
  name: string;
  descendant_count: number;
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
}

export interface OrgUnitUpdate {
  name?: string;
  parent_org_unit_id?: number | null;
  move_to_root?: boolean;
}

export interface OrgUnitMember {
  org_unit_id: number;
  name: string;
  unit_type: string;
  parent_org_unit_id: number | null;
  role: string | null;
}
