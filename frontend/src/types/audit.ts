export type AuditCategory = 'business' | 'admin' | 'auth' | 'security';

export type AuditStatus = 'success' | 'failure' | 'error';

export interface AuditLogItem {
  id: number;
  created_at: string;
  user_id: number | null;
  actor: string | null;
  /** Set when this row was written during an impersonated request (TF-742):
   *  the administrator actually behind `actor`, who is the target user. */
  impersonator: string | null;
  action: string;
  category: AuditCategory;
  resource_type: string | null;
  resource_id: string | null;
  status: AuditStatus;
  error_message: string | null;
  additional_data: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface AuditQueryParams {
  category?: AuditCategory[];
  action?: string;
  status?: AuditStatus;
  resource_type?: string;
  user_id?: number;
  institution_id?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}
