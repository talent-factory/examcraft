import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AdminOrgUnits from '../AdminOrgUnits';
import { OrgUnitsService } from '../../services/orgUnitsService';

jest.mock('../../services/orgUnitsService');
const mockedService = OrgUnitsService as jest.Mocked<typeof OrgUnitsService>;

// Local override of the global react-i18next mock (src/setupTests.ts): that
// mock recreates `t` as a brand-new closure on every `useTranslation()` call,
// whereas real i18next memoizes `t` across renders. AdminOrgUnits depends on
// `t` via `useCallback(load, [t])` + `useEffect(() => load(), [load])`; an
// unstable `t` makes that effect re-fire on every render, calling
// `OrgUnitsService.list()` in an unbounded loop and starving `waitFor`'s
// polling so it never reliably observes a settled DOM (intermittent
// timeouts). Giving `t` a stable identity here — scoped to this test file
// only — fixes the race without touching the shared setup file or the
// component (which correctly mirrors the same `useCallback` pattern already
// used by AdminGradingSchemes.tsx elsewhere in the codebase).
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

const theme = createTheme();
const renderWithTheme = () =>
  render(
    <ThemeProvider theme={theme}>
      <AdminOrgUnits />
    </ThemeProvider>,
  );

const abteilung = {
  id: 1,
  parent_org_unit_id: null,
  unit_type: 'abteilung',
  name: 'Informatik',
  descendant_count: 1,
  created_at: '2026-08-07T00:00:00Z',
  updated_at: '2026-08-07T00:00:00Z',
};

const team = {
  id: 2,
  parent_org_unit_id: 1,
  unit_type: 'team',
  name: 'Backend',
  descendant_count: 0,
  created_at: '2026-08-07T00:00:00Z',
  updated_at: '2026-08-07T00:00:00Z',
};

describe('AdminOrgUnits', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedService.list.mockResolvedValue({ items: [abteilung, team] });
  });

  it('renders the list of org units with resolved parent name', async () => {
    renderWithTheme();

    await waitFor(() => {
      expect(screen.getByTestId('ou-row-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('ou-row-2')).toBeInTheDocument();
    // "Informatik" appears twice: once as the parent row's own name, once as
    // the child row's resolved parent-name column — scope to the parent row
    // to avoid the ambiguous multi-match `getByText` query.
    expect(within(screen.getByTestId('ou-row-1')).getByText('Informatik')).toBeInTheDocument();
    expect(screen.getByText('Backend')).toBeInTheDocument();
  });

  it('opens the create dialog when clicking the create button', async () => {
    renderWithTheme();
    await waitFor(() => screen.getByTestId('ou-page-table'));

    fireEvent.click(screen.getByTestId('ou-page-create'));

    expect(screen.getByTestId('ou-editor-dialog')).toBeInTheDocument();
    expect(screen.getByText('Organisationseinheit anlegen')).toBeInTheDocument();
  });

  it('shows a descendant-count warning and deletes on confirm', async () => {
    mockedService.remove.mockResolvedValue(undefined);
    renderWithTheme();
    await waitFor(() => screen.getByTestId('ou-row-1'));

    fireEvent.click(screen.getByTestId('ou-btn-delete-1'));

    expect(
      screen.getByText(/Informatik.*1.*untergeordneten Einheiten/),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('ou-delete-confirm-btn'));

    await waitFor(() => {
      expect(mockedService.remove).toHaveBeenCalledWith(1);
    });
  });
});
