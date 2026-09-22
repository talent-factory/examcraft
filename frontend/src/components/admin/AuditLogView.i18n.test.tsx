/**
 * AuditLogView against the real German copy.
 *
 * Separate from AuditLogView.test.tsx on purpose: that file replaces
 * react-i18next with a key-echoing mock, under which a missing locale key and
 * a present one render identically. Here the global mock from setupTests.ts
 * resolves keys against de/translation.json and returns the bare key when one
 * is missing, so these assertions fail on a missing key as well as on a
 * hardcoded literal.
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AuditLogView from './AuditLogView';
import * as auditService from '../../services/auditService';
import { AuditLogItem, AuditLogListResponse } from '../../types/audit';

const row = (id: number, status: string): AuditLogItem => ({
  id, created_at: '2026-06-13T10:00:00Z', user_id: 5, actor: 'Test User',
  impersonator: null,
  action: 'create_document', category: 'business', resource_type: 'document',
  resource_id: '42',
  // The DB column is a free String(20); the cast lets a test feed the value
  // the type rules out but the backend could still send.
  status: status as AuditLogItem['status'],
  error_message: null, additional_data: null, ip_address: null, user_agent: null,
});

const response = (items: AuditLogItem[]): AuditLogListResponse => ({
  items, total: items.length, limit: 25, offset: 0, has_more: false,
});

describe('AuditLogView — German copy (TF-775)', () => {
  afterEach(() => jest.restoreAllMocks());

  it('names the table in the UI language', async () => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(response([row(1, 'success')]));
    render(<AuditLogView isSuperuser={false} />);

    expect(await screen.findByRole('table', { name: 'Audit-Log' })).toBeInTheDocument();
    expect(screen.queryByRole('table', { name: 'audit-log' })).not.toBeInTheDocument();
  });

  it('offers the status filter values translated', async () => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(response([]));
    render(<AuditLogView isSuperuser={false} />);

    await userEvent.click(
      within(screen.getByTestId('audit-filter-status')).getByRole('combobox'),
    );
    const options = (await screen.findAllByRole('option')).map((o) => o.textContent);
    expect(options).toEqual(['Alle', 'Erfolgreich', 'Fehlgeschlagen', 'Fehler']);
  });

  // MUI renders nothing for value '' without displayEmpty; the label then sat
  // in the field as a grey placeholder and "Alle" never appeared once chosen.
  it('shows "Alle" in both filters while no value is selected', async () => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(response([]));
    render(<AuditLogView isSuperuser={false} />);

    for (const id of ['audit-filter-category', 'audit-filter-status']) {
      expect(within(screen.getByTestId(id)).getByRole('combobox')).toHaveTextContent('Alle');
    }
  });

  it('shows the status column with the same words as the filter', async () => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(
      response([row(1, 'success'), row(2, 'failure'), row(3, 'error')]),
    );
    render(<AuditLogView isSuperuser={false} />);

    expect(await screen.findByText('Erfolgreich')).toBeInTheDocument();
    expect(screen.getByText('Fehlgeschlagen')).toBeInTheDocument();
    expect(screen.getByText('Fehler')).toBeInTheDocument();
    expect(screen.queryByText('success')).not.toBeInTheDocument();
  });

  it.each(['timeout', ''])('shows an unknown status value %j raw instead of a key path, flagged as unrecognized', async (status) => {
    jest.spyOn(auditService, 'fetchAuditLogs').mockResolvedValue(response([row(1, status)]));
    render(<AuditLogView isSuperuser={false} />);

    // toHaveTextContent('') only passes when the element's text is genuinely
    // empty (jest-dom special-cases an empty `checkWith` to require an empty
    // `textContent`), so this also covers the status: '' case correctly.
    const flagged = await screen.findByTitle('Unbekannter Status — kein bekannter Wert für dieses Feld.');
    expect(flagged).toHaveTextContent(status);
    expect(screen.queryByText(/pages\.admin\.audit\.status/)).not.toBeInTheDocument();
  });
});
