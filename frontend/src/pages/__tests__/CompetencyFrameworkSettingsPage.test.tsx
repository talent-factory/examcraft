import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CompetencyFrameworkSettingsPage from '../CompetencyFrameworkSettingsPage';
import type { CompetencyFramework } from '../../types/competencyFramework';

jest.mock('../../api/competencyFrameworksApi', () => ({
  competencyFrameworksApi: {
    listFrameworks: jest.fn(),
    createFramework: jest.fn(),
    updateFramework: jest.fn(),
    archiveFramework: jest.fn(),
    unarchiveFramework: jest.fn(),
  },
}));
import { competencyFrameworksApi } from '../../api/competencyFrameworksApi';
const mockList = competencyFrameworksApi.listFrameworks as jest.Mock;
const mockArchive = competencyFrameworksApi.archiveFramework as jest.Mock;

let mockIsAdmin = false;
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, is_superuser: false },
    hasPermission: (p: string) => (mockIsAdmin && p === 'manage_settings') || p === 'create_questions',
  }),
}));

// Form as a stub — the page test checks list/filter/actions, not the form.
jest.mock('../../components/competencyFrameworks/CompetencyFrameworkForm', () => () => (
  <div data-testid="framework-form" />
));

const makeFrameworks = (): CompetencyFramework[] => [
  {
    id: 1, name: 'Modul A – Mitarbeitende führen', module_code: 'A', description: null,
    rendered_text: 'VA', language: 'de', institution_id: 10, created_by: 1,
    visibility: 'institution', is_archived: false,
    competencies: [{ id: 11, code: 'A1', title: 'Führen', descriptors: null, position: 0 }],
  },
  {
    id: 2, name: 'Modul B – Wirkungsvoll kommunizieren', module_code: 'B', description: null,
    rendered_text: 'VB', language: 'de', institution_id: 10, created_by: 99,
    visibility: 'institution', is_archived: false,
    competencies: [{ id: 21, code: 'B3', title: 'Konflikte', descriptors: null, position: 0 }],
  },
];

const renderPage = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CompetencyFrameworkSettingsPage />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  mockIsAdmin = false;
  localStorage.clear();
  mockList.mockResolvedValue(makeFrameworks());
  mockArchive.mockResolvedValue({ ...makeFrameworks()[0], is_archived: true });
});

it('listet Frameworks inkl. Competency-Codes', async () => {
  renderPage();
  expect(await screen.findByText(/Modul A/)).toBeInTheDocument();
  expect(await screen.findByText(/Modul B/)).toBeInTheDocument();
  expect(screen.getByText(/A1/)).toBeInTheDocument();
  expect(screen.getByText(/B3/)).toBeInTheDocument();
});

it('zeigt Aktionen nur für eigene Frameworks (created_by === user.id)', async () => {
  renderPage();
  await screen.findByText(/Modul A/);
  // Modul A belongs to user 1 → archive button present; Modul B (created_by 99) → not.
  const archiveButtons = screen.getAllByRole('button', { name: /Archivieren/i });
  expect(archiveButtons).toHaveLength(1);
});

it('lädt archivierte Frameworks, wenn Filter auf "Archiviert" wechselt', async () => {
  renderPage();
  await screen.findByText(/Modul A/);
  fireEvent.click(screen.getByRole('button', { name: /Archiviert/i }));
  await waitFor(() => expect(mockList).toHaveBeenCalledWith(true));
});

it('öffnet das Formular beim Klick auf "Neuer Kompetenzrahmen"', async () => {
  renderPage();
  await screen.findByText(/Modul A/);
  fireEvent.click(screen.getByRole('button', { name: /Neuer Kompetenzrahmen/i }));
  expect(await screen.findByTestId('framework-form')).toBeInTheDocument();
});

// TF-772 PR 7: the page used to render `response.data.detail` through a local
// extractApiDetail(). It now renders the backend's error_code translated, and
// the operation fallback without one — never the raw detail.
const axiosError = (status: number, data: Record<string, unknown>) =>
  Object.assign(new Error(`Request failed with status code ${status}`), {
    response: { status, data },
  });

it('zeigt einen Archiv-Fehler über den error_code, nicht über detail', async () => {
  mockArchive.mockRejectedValue(
    axiosError(403, { detail: 'ROHER BACKEND-TEXT', error_code: 'competency_frameworks_access_denied' }),
  );
  renderPage();
  await screen.findByText(/Modul A/);
  fireEvent.click(screen.getByRole('button', { name: /Archivieren/i }));

  expect(await screen.findByText('Zugriff verweigert.')).toBeInTheDocument();
  expect(screen.queryByText('ROHER BACKEND-TEXT')).not.toBeInTheDocument();
});

it('zeigt beim Ladefehler ohne Code den Operationssatz, nicht detail', async () => {
  mockList.mockRejectedValue(axiosError(500, { detail: 'ROHER BACKEND-TEXT' }));
  renderPage();

  expect(
    await screen.findByText('Kompetenzrahmen konnten nicht geladen werden.'),
  ).toBeInTheDocument();
  expect(screen.queryByText('ROHER BACKEND-TEXT')).not.toBeInTheDocument();
});
