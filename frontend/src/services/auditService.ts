import { getJson } from './httpClient';
import { AuditLogListResponse, AuditQueryParams } from '../types/audit';

/** Fetch a page of audit-log entries. Scope is enforced server-side by role. */
export async function fetchAuditLogs(
  params: AuditQueryParams = {}
): Promise<AuditLogListResponse> {
  const qs = new URLSearchParams();
  if (params.category?.length) qs.append('category', params.category.join(','));
  if (params.action) qs.append('action', params.action);
  if (params.status) qs.append('status', params.status);
  if (params.resource_type) qs.append('resource_type', params.resource_type);
  if (params.user_id != null) qs.append('user_id', String(params.user_id));
  if (params.institution_id != null) qs.append('institution_id', String(params.institution_id));
  if (params.date_from) qs.append('date_from', params.date_from);
  if (params.date_to) qs.append('date_to', params.date_to);
  if (params.limit != null) qs.append('limit', String(params.limit));
  if (params.offset != null) qs.append('offset', String(params.offset));
  const query = qs.toString();
  return getJson<AuditLogListResponse>(`/api/v1/audit${query ? `?${query}` : ''}`);
}
