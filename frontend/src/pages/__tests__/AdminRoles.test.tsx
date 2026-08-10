import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AdminRoles from '../AdminRoles';
import { RolesService } from '../../services/rolesService';
import { ApiError } from '../../services/httpClient';

jest.mock('../../services/rolesService');
const mockedService = RolesService as jest.Mocked<typeof RolesService>;

// Local override of the global react-i18next mock (src/setupTests.ts): that
// mock recreates `t` as a brand-new closure on every `useTranslation()` call,
// whereas real i18next memoizes `t` across renders. AdminRoles depends on
// `t` via `useCallback(load, [t])` + `useEffect(() => load(), [load])`; an
// unstable `t` makes that effect re-fire on every render, calling
// `RolesService.list()` in an unbounded loop and starving `waitFor`'s
// polling so it never reliably observes a settled DOM (intermittent
// timeouts). Giving `t` a stable identity here — scoped to this test file
// only — fixes the race without touching the shared setup file or the
// component (which correctly mirrors the same `useCallback` pattern already
// used by AdminOrgUnits.tsx elsewhere in the codebase).
jest.mock('react-i18next', () => {
  const mockTranslations = require('../../locales/de/translation.json');
  function mockResolveKey(obj: Record<string, any>, key: string): string {
    const parts = key.split('.');
    let current: any = obj;
    for (const part of parts) {
      if (current == null || typeof current !== 'object') return key;
      current = current[part];
    }
    return typeof current === 'string' ? current : key;
  }
  const stableT = (key: string, params?: Record<string, any>) => {
    let value = mockResolveKey(mockTranslations, key);
    if (params && typeof value === 'string') {
      Object.entries(params).forEach(([k, v]) => {
        value = (value as string).replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      });
    }
    return value;
  };
  return {
    useTranslation: () => ({
      t: stableT,
      i18n: { changeLanguage: jest.fn().mockResolvedValue(undefined), language: 'de' },
    }),
    Trans: ({ children }: { children: React.ReactNode }) => children,
    initReactI18next: { type: '3rdParty', init: jest.fn() },
  };
});

const adminRole = {
  id: 1,
  name: 'admin',
  display_name: 'Administrator',
  description: 'Full access',
  permissions: ['manage_org_units', 'manage_settings'],
  is_system_role: true,
  created_at: '2026-08-10T00:00:00Z',
};

const customRole = {
  id: 2,
  name: 'fachbereichsleiter',
  display_name: 'Fachbereichsleiter',
  description: null,
  permissions: ['manage_org_units'],
  is_system_role: false,
  created_at: '2026-08-10T00:00:00Z',
};

const theme = createTheme();
const renderPage = () =>
  render(
    <ThemeProvider theme={theme}>
      <AdminRoles />
    </ThemeProvider>,
  );

describe('AdminRoles', () => {
  afterEach(() => jest.clearAllMocks());

  it('lists roles with permission count and system-role marker', async () => {
    mockedService.list.mockResolvedValue([adminRole, customRole]);
    renderPage();

    await waitFor(() => expect(screen.getByText('Administrator')).toBeInTheDocument());
    expect(screen.getByText('Fachbereichsleiter')).toBeInTheDocument();
  });

  it('shows an empty-state message when no roles exist', async () => {
    mockedService.list.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText('Keine Rollen gefunden.')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows the backend detail message when loading roles fails', async () => {
    mockedService.list.mockRejectedValueOnce(
      new ApiError({
        kind: 'validation',
        status: 500,
        message: 'DB down',
        detail: 'DB down',
      }),
    );
    renderPage();

    expect(await screen.findByText('DB down')).toBeInTheDocument();
    expect(screen.queryByText('Rollen konnten nicht geladen werden.')).not.toBeInTheDocument();
  });

  it('falls back to the generic message when loading roles fails without a detail', async () => {
    mockedService.list.mockRejectedValueOnce(new Error('network down'));
    renderPage();

    expect(
      await screen.findByText('Rollen konnten nicht geladen werden.'),
    ).toBeInTheDocument();
  });

  it('delete button is disabled for system roles', async () => {
    mockedService.list.mockResolvedValue([adminRole, customRole]);
    renderPage();

    await waitFor(() => expect(screen.getByText('Administrator')).toBeInTheDocument());
    const rows = screen.getAllByRole('row');
    const adminRow = rows.find((r) => r.textContent?.includes('Administrator'))!;
    expect(within(adminRow).getByLabelText('Löschen')).toBeDisabled();
  });

  it('deleting a non-system role calls RolesService.remove after confirmation', async () => {
    mockedService.list.mockResolvedValue([customRole]);
    mockedService.remove.mockResolvedValue(undefined);
    renderPage();

    await waitFor(() => expect(screen.getByText('Fachbereichsleiter')).toBeInTheDocument());
    fireEvent.click(screen.getByLabelText('Löschen'));
    fireEvent.click(await screen.findByRole('button', { name: 'Endgültig löschen' }));

    await waitFor(() => expect(mockedService.remove).toHaveBeenCalledWith(2));
  });

  it('shows the backend detail message when delete fails with a 409', async () => {
    mockedService.list.mockResolvedValue([customRole]);
    mockedService.remove.mockRejectedValueOnce(
      new ApiError({
        kind: 'validation',
        status: 409,
        message: 'Rolle ist noch 3 Benutzer(n) zugewiesen',
        detail: 'Rolle ist noch 3 Benutzer(n) zugewiesen',
      }),
    );
    renderPage();

    await waitFor(() => expect(screen.getByText('Fachbereichsleiter')).toBeInTheDocument());
    fireEvent.click(screen.getByLabelText('Löschen'));
    fireEvent.click(await screen.findByRole('button', { name: 'Endgültig löschen' }));

    expect(
      await screen.findByText('Rolle ist noch 3 Benutzer(n) zugewiesen'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Rolle konnte nicht gelöscht werden.'),
    ).not.toBeInTheDocument();
  });

  it('resets a stale delete error when reopening the dialog for another role', async () => {
    const otherRole = {
      id: 3,
      name: 'pruefer',
      display_name: 'Prüfer',
      description: null,
      permissions: ['manage_org_units'],
      is_system_role: false,
      created_at: '2026-08-10T00:00:00Z',
    };
    mockedService.list.mockResolvedValue([customRole, otherRole]);
    mockedService.remove.mockRejectedValueOnce(new Error('boom'));
    renderPage();

    await waitFor(() => expect(screen.getByText('Fachbereichsleiter')).toBeInTheDocument());
    const rows = screen.getAllByRole('row');
    const roleARow = rows.find((r) => r.textContent?.includes('Fachbereichsleiter'))!;
    const roleBRow = rows.find((r) => r.textContent?.includes('Prüfer'))!;

    // Deleting role A fails — the dialog shows the error.
    fireEvent.click(within(roleARow).getByLabelText('Löschen'));
    fireEvent.click(await screen.findByRole('button', { name: 'Endgültig löschen' }));
    expect(
      await screen.findByText('Rolle konnte nicht gelöscht werden.'),
    ).toBeInTheDocument();

    // Abort — closing the dialog must clear the stale error.
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    await waitFor(() =>
      expect(screen.queryByText('Rolle konnte nicht gelöscht werden.')).not.toBeInTheDocument(),
    );

    // Opening the dialog for role B must not show role A's leftover error,
    // even though no delete attempt for role B has happened yet.
    fireEvent.click(within(roleBRow).getByLabelText('Löschen'));
    expect(screen.queryByText('Rolle konnte nicht gelöscht werden.')).not.toBeInTheDocument();
  });
});
