import React from 'react';
import { render, screen } from '@testing-library/react';
import AuditLogView from './AuditLogView';
import * as auditService from '../../services/auditService';
import { AuditLogListResponse } from '../../types/audit';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

const oneRow: AuditLogListResponse = {
  items: [{
    id: 1, created_at: '2026-06-13T10:00:00Z', user_id: 5, actor: 'Test User',
    action: 'create_document', category: 'business', resource_type: 'document',
    resource_id: '42', status: 'success', error_message: null,
    additional_data: null, ip_address: null, user_agent: null,
  }],
  total: 1, limit: 25, offset: 0, has_more: false,
};

describe('AuditLogView', () => {
  afterEach(() => jest.restoreAllMocks());

  it('fetches and renders an audit row', async () => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(oneRow);
    render(<AuditLogView isSuperuser={false} />);
    expect(await screen.findByText('create_document')).toBeInTheDocument();
    expect(screen.getByText('Test User')).toBeInTheDocument();
  });

  it('shows the institution filter only for superusers', async () => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(oneRow);
    const { rerender } = render(<AuditLogView isSuperuser={false} />);
    await screen.findByText('create_document');
    expect(screen.queryByTestId('audit-filter-institution')).toBeNull();

    rerender(<AuditLogView isSuperuser={true} />);
    expect(await screen.findByTestId('audit-filter-institution')).toBeInTheDocument();
  });
});
