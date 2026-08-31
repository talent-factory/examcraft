import { fetchAuditLogs } from './auditService';
import * as httpClient from './httpClient';
import { AuditLogListResponse } from '../types/audit';

const empty: AuditLogListResponse = {
  items: [], total: 0, limit: 25, offset: 0, has_more: false,
};

describe('auditService.fetchAuditLogs', () => {
  it('builds a query string from filters and calls /api/v1/audit', async () => {
    const spy = jest.spyOn(httpClient, 'getJson').mockResolvedValue(empty);
    await fetchAuditLogs({ category: ['business', 'admin'], status: 'success', limit: 50, offset: 25 });
    expect(spy).toHaveBeenCalledTimes(1);
    const calledPath = spy.mock.calls[0][0] as string;
    expect(calledPath.startsWith('/api/v1/audit?')).toBe(true);
    expect(calledPath).toContain('category=business%2Cadmin');
    expect(calledPath).toContain('status=success');
    expect(calledPath).toContain('limit=50');
    expect(calledPath).toContain('offset=25');
    spy.mockRestore();
  });

  it('omits the query string when no params are given', async () => {
    const spy = jest.spyOn(httpClient, 'getJson').mockResolvedValue(empty);
    await fetchAuditLogs();
    expect(spy).toHaveBeenCalledWith('/api/v1/audit');
    spy.mockRestore();
  });

  it('passes a CSV `action` filter through untouched (TF-761: impersonation-only filter)', async () => {
    const spy = jest.spyOn(httpClient, 'getJson').mockResolvedValue(empty);
    await fetchAuditLogs({ action: 'impersonation.start,impersonation.end' });
    const calledPath = spy.mock.calls[0][0] as string;
    expect(calledPath).toContain('action=impersonation.start%2Cimpersonation.end');
    spy.mockRestore();
  });
});
