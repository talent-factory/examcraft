import React from 'react';
import { render, screen } from '@testing-library/react';
import AuditLogView from './AuditLogView';
import * as auditService from '../../services/auditService';
import { AuditLogListResponse } from '../../types/audit';

jest.mock('react-i18next', () => ({
  // Test-quality review fix: the previous mock discarded the interpolation
  // options entirely (`t: (k) => k`), so a test asserting on the chip's
  // presence alone couldn't tell whether `row.impersonator` (correct) or
  // e.g. `row.actor` (a plausible copy/paste regression) had actually been
  // passed into `t(...)`. Folding the options into the returned string
  // lets assertions check the real value ended up in the rendered output,
  // without depending on the actual translation copy.
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key} ${JSON.stringify(options)}` : key,
  }),
}));

const oneRow: AuditLogListResponse = {
  items: [{
    id: 1, created_at: '2026-06-13T10:00:00Z', user_id: 5, actor: 'Test User',
    impersonator: null,
    action: 'create_document', category: 'business', resource_type: 'document',
    resource_id: '42', status: 'success', error_message: null,
    additional_data: null, ip_address: null, user_agent: null,
  }],
  total: 1, limit: 25, offset: 0, has_more: false,
};

const impersonatedRow: AuditLogListResponse = {
  items: [{
    id: 2, created_at: '2026-08-30T10:00:00Z', user_id: 5, actor: 'Target User',
    impersonator: 'Admin Person',
    action: 'impersonation.end', category: 'admin', resource_type: 'user',
    resource_id: '5', status: 'success', error_message: null,
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

  it('marks an impersonated row with a badge, non-impersonated rows without', async () => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(oneRow);
    render(<AuditLogView isSuperuser={false} />);
    await screen.findByText('create_document');
    expect(screen.queryByTestId('audit-impersonated-chip')).toBeNull();
  });

  it('shows who impersonated whom on an impersonation.end row', async () => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(impersonatedRow);
    render(<AuditLogView isSuperuser={false} />);
    await screen.findByText('impersonation.end');
    expect(screen.getByText('Target User')).toBeInTheDocument();
    const chip = screen.getByTestId('audit-impersonated-chip');
    expect(chip).toBeInTheDocument();
    // Review fix: prove `row.impersonator` (not e.g. `row.actor`) is what
    // actually reaches `t(...)` for both the label and the tooltip.
    expect(chip).toHaveTextContent('Admin Person');
    expect(chip.title).toContain('Admin Person');
  });
});
