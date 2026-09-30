/**
 * `/portfolio` list (TF-989): columns, filters, paging, delete with confirmation.
 */
import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PortfolioAssessmentsPage from '../PortfolioAssessmentsPage';
import { portfolioApi } from '../../../api/portfolioApi';
import { AppError } from '../../../errors';
import type {
  PortfolioAssessmentJob,
  PortfolioAssessmentListItem,
  PortfolioAssessmentListPage,
} from '../../../types/portfolio';

jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ tier: 'professional', isLoading: false }),
}));

let mockPermissions: string[] = [];
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ hasPermission: (p: string) => mockPermissions.includes(p) }),
}));

jest.mock('../../../api/portfolioApi', () => ({
  portfolioApi: {
    listAssessments: jest.fn(),
    listTemplates: jest.fn(),
    deleteAssessment: jest.fn(),
  },
}));

// The dialog has its own tests; here only its hand-off to the detail page matters.
jest.mock('../../../components/portfolio/PortfolioAssessmentCreateDialog', () => ({
  PortfolioAssessmentCreateDialog: ({
    open,
    onCreated,
  }: {
    open: boolean;
    onCreated: (id: string) => void;
  }) =>
    open ? (
      <div data-testid="mock-create-dialog">
        <button onClick={() => onCreated('a-9')}>mock-created</button>
      </div>
    ) : null,
}));

const api = portfolioApi as jest.Mocked<typeof portfolioApi>;

function job(overrides: Partial<PortfolioAssessmentJob> = {}): PortfolioAssessmentJob {
  return {
    id: 'job-1',
    job_type: 'ingest',
    status: 'completed',
    files_total: 12,
    files_done: 12,
    error_log: null,
    created_at: null,
    started_at: null,
    finished_at: null,
    ...overrides,
  };
}

function item(overrides: Partial<PortfolioAssessmentListItem> = {}): PortfolioAssessmentListItem {
  return {
    id: 'a-1',
    template_id: 't-1',
    template_version: 1,
    student_id: 7,
    created_by: 1,
    status: 'classifying',
    framework_conditions: null,
    source_repository_url: null,
    source_repository_ref: null,
    grading_scheme_id: null,
    review_status: 'pending_review',
    overall_points_awarded: null,
    overall_points_max: null,
    overall_percentage: null,
    created_at: null,
    updated_at: null,
    job: job(),
    student_name: 'Mia Muster',
    student_external_id: 'mia@schule.ch',
    template_name: 'IPA Informatik',
    ...overrides,
  };
}

function page(items: PortfolioAssessmentListItem[], total = items.length): PortfolioAssessmentListPage {
  return { items, total, limit: 25, offset: 0 };
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/portfolio']}>
        <Routes>
          <Route path="/portfolio" element={<PortfolioAssessmentsPage />} />
          <Route path="/portfolio/:id" element={<div data-testid="detail-route" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.resetAllMocks();
  mockPermissions = [
    'portfolio_assessments:read',
    'portfolio_assessments:manage',
    'portfolio_templates:read',
  ];
  api.listTemplates.mockResolvedValue([
    { id: 't-1', name: 'IPA Informatik', is_active: true },
  ] as never);
});

describe('PortfolioAssessmentsPage', () => {
  it('zeigt Person, Template, Status- und Review-Chips und den letzten Auftrag', async () => {
    api.listAssessments.mockResolvedValue(page([item()]));
    renderPage();

    const row = await screen.findByTestId('portfolio-row-a-1');
    expect(within(row).getByText('Mia Muster')).toBeInTheDocument();
    expect(within(row).getByText('mia@schule.ch')).toBeInTheDocument();
    expect(within(row).getByText('IPA Informatik')).toBeInTheDocument();
    expect(within(row).getByText('Klassifikation')).toBeInTheDocument();
    expect(within(row).getByText('Offen')).toBeInTheDocument();
    expect(within(row).getByText('Import · Abgeschlossen')).toBeInTheDocument();
    expect(within(row).getByText('12 von 12 Dateien')).toBeInTheDocument();
    expect(api.listAssessments).toHaveBeenCalledWith({ limit: 25, offset: 0 });
  });

  it('filtert serverseitig nach Status und springt auf die erste Seite', async () => {
    api.listAssessments.mockResolvedValue(page([item()], 60));
    renderPage();
    await screen.findByTestId('portfolio-row-a-1');

    fireEvent.click(screen.getByRole('button', { name: /next page|nächste seite/i }));
    await waitFor(() =>
      expect(api.listAssessments).toHaveBeenLastCalledWith({ limit: 25, offset: 25 }),
    );

    fireEvent.mouseDown(within(screen.getByTestId('portfolio-filter-status')).getByRole('combobox'));
    fireEvent.click(await screen.findByRole('option', { name: 'Fehlgeschlagen' }));
    await waitFor(() =>
      expect(api.listAssessments).toHaveBeenLastCalledWith({
        status: 'failed',
        limit: 25,
        offset: 0,
      }),
    );
  });

  it('filtert nach Template und Review-Status', async () => {
    api.listAssessments.mockResolvedValue(page([item()]));
    renderPage();
    await screen.findByTestId('portfolio-row-a-1');

    fireEvent.mouseDown(within(screen.getByTestId('portfolio-filter-template')).getByRole('combobox'));
    fireEvent.click(await screen.findByRole('option', { name: 'IPA Informatik' }));
    fireEvent.mouseDown(within(screen.getByTestId('portfolio-filter-review')).getByRole('combobox'));
    fireEvent.click(await screen.findByRole('option', { name: 'Überprüft' }));
    await waitFor(() =>
      expect(api.listAssessments).toHaveBeenLastCalledWith({
        template_id: 't-1',
        review_status: 'fully_reviewed',
        limit: 25,
        offset: 0,
      }),
    );
  });

  it('meldet leere Filtertreffer anders als eine leere Liste', async () => {
    api.listAssessments.mockResolvedValue(page([]));
    renderPage();
    expect(await screen.findByText('Noch keine Portfolio-Bewertungen vorhanden.')).toBeInTheDocument();

    fireEvent.mouseDown(within(screen.getByTestId('portfolio-filter-status')).getByRole('combobox'));
    fireEvent.click(await screen.findByRole('option', { name: 'Bewertet' }));
    expect(
      await screen.findByText('Keine Portfolio-Bewertungen für diese Filter.'),
    ).toBeInTheDocument();
  });

  it('löscht nach Bestätigung und lädt die Liste neu', async () => {
    api.listAssessments.mockResolvedValue(page([item()]));
    api.deleteAssessment.mockResolvedValue({ id: 'a-1' });
    renderPage();

    fireEvent.click(await screen.findByTestId('portfolio-delete-a-1'));
    expect(screen.getByText(/Mia Muster \(IPA Informatik\)/)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('portfolio-delete-confirm'));

    await waitFor(() => expect(api.deleteAssessment).toHaveBeenCalledWith('a-1'));
    await waitFor(() => expect(api.listAssessments).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.queryByTestId('portfolio-delete-confirm')).not.toBeInTheDocument(),
    );
  });

  it('zeigt eine 409 wegen laufendem Auftrag im Dialog an', async () => {
    api.listAssessments.mockResolvedValue(page([item()]));
    api.deleteAssessment.mockRejectedValue(
      new AppError('portfolio_assessment_delete_job_active', 'x', 409),
    );
    renderPage();

    fireEvent.click(await screen.findByTestId('portfolio-delete-a-1'));
    fireEvent.click(screen.getByTestId('portfolio-delete-confirm'));
    expect(
      await screen.findByText(/Sie kann erst gelöscht werden, wenn diese abgeschlossen ist/),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-delete-confirm')).toBeInTheDocument();
  });

  it('sperrt das Löschen, solange ein Auftrag läuft', async () => {
    api.listAssessments.mockResolvedValue(
      page([item({ status: 'uploading', job: job({ status: 'running', files_done: 3 }) })]),
    );
    renderPage();
    expect(await screen.findByTestId('portfolio-delete-a-1')).toBeDisabled();
    expect(screen.getByText('3 von 12 Dateien')).toBeInTheDocument();
  });

  it('öffnet nach dem Anlegen die Detailseite', async () => {
    api.listAssessments.mockResolvedValue(page([]));
    renderPage();
    fireEvent.click(await screen.findByTestId('portfolio-create-open'));
    expect(await screen.findByTestId('mock-create-dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByText('mock-created'));
    expect(await screen.findByTestId('detail-route')).toBeInTheDocument();
  });

  it('frischt die Liste auf, solange ein Auftrag läuft', async () => {
    jest.useFakeTimers();
    try {
      api.listAssessments
        .mockResolvedValueOnce(
          page([item({ status: 'uploading', job: job({ status: 'running', files_done: 3 }) })]),
        )
        .mockResolvedValue(page([item()]));
      renderPage();
      expect(await screen.findByText('3 von 12 Dateien')).toBeInTheDocument();
      jest.advanceTimersByTime(5000);
      expect(await screen.findByText('12 von 12 Dateien')).toBeInTheDocument();
      const calls = api.listAssessments.mock.calls.length;
      jest.advanceTimersByTime(15000);
      expect(api.listAssessments).toHaveBeenCalledTimes(calls);
    } finally {
      jest.useRealTimers();
    }
  });

  it('blättert zurück, wenn die letzte Zeile der letzten Seite gelöscht wurde', async () => {
    api.listAssessments.mockResolvedValue(page([item()], 26));
    api.deleteAssessment.mockResolvedValue({ id: 'a-1' });
    renderPage();
    await screen.findByTestId('portfolio-row-a-1');
    fireEvent.click(screen.getByRole('button', { name: /next page|nächste seite/i }));
    await waitFor(() =>
      expect(api.listAssessments).toHaveBeenLastCalledWith({ limit: 25, offset: 25 }),
    );

    api.listAssessments.mockImplementation(async (params) =>
      params?.offset ? page([], 25) : page([item({ id: 'a-2' })], 25),
    );
    fireEvent.click(await screen.findByTestId('portfolio-delete-a-1'));
    fireEvent.click(screen.getByTestId('portfolio-delete-confirm'));
    await waitFor(() =>
      expect(api.listAssessments).toHaveBeenLastCalledWith({ limit: 25, offset: 0 }),
    );
  });

  it('behandelt eine 404 beim Löschen als erledigt', async () => {
    api.listAssessments.mockResolvedValue(page([item()]));
    api.deleteAssessment.mockRejectedValue(
      new AppError('portfolio_assessment_not_found', 'x', 404),
    );
    renderPage();
    fireEvent.click(await screen.findByTestId('portfolio-delete-a-1'));
    fireEvent.click(screen.getByTestId('portfolio-delete-confirm'));
    await waitFor(() =>
      expect(screen.queryByTestId('portfolio-delete-confirm')).not.toBeInTheDocument(),
    );
    await waitFor(() => expect(api.listAssessments).toHaveBeenCalledTimes(2));
  });

  it('löscht bei «Abbrechen» nichts', async () => {
    api.listAssessments.mockResolvedValue(page([item()]));
    renderPage();
    fireEvent.click(await screen.findByTestId('portfolio-delete-a-1'));
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    await waitFor(() =>
      expect(screen.queryByTestId('portfolio-delete-confirm')).not.toBeInTheDocument(),
    );
    expect(api.deleteAssessment).not.toHaveBeenCalled();
  });

  it('zeigt einen Ladefehler der Liste übersetzt an', async () => {
    api.listAssessments.mockRejectedValue(new AppError('portfolio_assessment_list_failed'));
    renderPage();
    expect(
      await screen.findByText('Die Portfolio-Bewertungen konnten nicht geladen werden.'),
    ).toBeInTheDocument();
  });

  it('zeigt bei einer Tier-Ablehnung der Liste den Upgrade-Hinweis', async () => {
    api.listAssessments.mockRejectedValue(
      new AppError('portfolio_assessment_tier_insufficient', 'x', 403),
    );
    renderPage();
    expect(await screen.findByText('Benötigter Tarif')).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-assessments-page')).not.toBeInTheDocument();
  });

  it('meldet einen Ladefehler der Templates statt einer leeren Filterliste', async () => {
    api.listAssessments.mockResolvedValue(page([item()]));
    api.listTemplates.mockRejectedValue(new AppError('portfolio_template_list_failed'));
    renderPage();
    expect(await screen.findByText('Die Templates konnten nicht geladen werden.')).toBeInTheDocument();
  });

  it('lädt ohne Template-Leserecht keine Templates und zeigt keinen Template-Filter', async () => {
    mockPermissions = ['portfolio_assessments:read'];
    api.listAssessments.mockResolvedValue(page([item()]));
    renderPage();
    await screen.findByTestId('portfolio-row-a-1');
    expect(screen.queryByTestId('portfolio-filter-template')).not.toBeInTheDocument();
    expect(api.listTemplates).not.toHaveBeenCalled();
  });

  it('zeigt ohne Verwaltungsrecht weder Anlegen noch Löschen', async () => {
    mockPermissions = ['portfolio_assessments:read'];
    api.listAssessments.mockResolvedValue(page([item()]));
    renderPage();
    await screen.findByTestId('portfolio-row-a-1');
    expect(screen.queryByTestId('portfolio-create-open')).not.toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-delete-a-1')).not.toBeInTheDocument();
  });
});
