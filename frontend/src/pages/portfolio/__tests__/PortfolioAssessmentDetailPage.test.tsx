/**
 * Detail scaffold: step branching, job panel, «läuft seit …» (TF-987).
 */
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PortfolioAssessmentDetailPage from '../PortfolioAssessmentDetailPage';
import { portfolioApi } from '../../../api/portfolioApi';
import { AppError } from '../../../errors';
import type {
  PortfolioAssessmentDetail,
  PortfolioAssessmentJob,
  PortfolioAssessmentStatus,
} from '../../../types/portfolio';

jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ tier: 'professional', isLoading: false }),
}));

// Read-only by default: the upload step then shows its placeholder. The
// ingestion panel has its own tests (PortfolioIngestionPanel.test.tsx).
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ hasPermission: () => false }),
}));

jest.mock('../../../api/portfolioApi', () => ({
  // getTemplate: the classification and grading steps load phase names (TF-990, TF-991).
  portfolioApi: { getAssessment: jest.fn(), getTemplate: jest.fn() },
}));

const getAssessment = portfolioApi.getAssessment as jest.Mock;
const getTemplate = portfolioApi.getTemplate as jest.Mock;

function assessment(
  status: PortfolioAssessmentStatus,
  job: PortfolioAssessmentJob | null,
): PortfolioAssessmentDetail {
  return {
    id: 'a-1',
    template_id: 't-1',
    template_version: 1,
    student_id: 7,
    created_by: 1,
    status,
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
    job,
    documents: [],
    phase_results: [],
    overall_grade: null,
  };
}

function job(overrides: Partial<PortfolioAssessmentJob> = {}): PortfolioAssessmentJob {
  return {
    id: 'job-1',
    job_type: 'ingest',
    status: 'running',
    files_total: null,
    files_done: 0,
    error_log: null,
    created_at: null,
    started_at: null,
    finished_at: null,
    ...overrides,
  };
}

const minutesAgo = (minutes: number) => new Date(Date.now() - minutes * 60 * 1000).toISOString();

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/portfolio/a-1']}>
        <Routes>
          <Route path="/portfolio/:id" element={<PortfolioAssessmentDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  getAssessment.mockReset();
  getTemplate.mockReset().mockResolvedValue({ id: 't-1', phases: [] });
});

describe('PortfolioAssessmentDetailPage', () => {
  it.each<[PortfolioAssessmentStatus, string]>([
    ['uploading', 'upload'],
    ['failed', 'upload'],
    ['classifying', 'classification'],
    ['ready_to_grade', 'grading'],
    ['grading', 'grading'],
    ['completed', 'review'],
  ])('verzweigt bei Status %s auf den Abschnitt %s', async (status, section) => {
    getAssessment.mockResolvedValue(assessment(status, null));
    renderPage();
    expect(await screen.findByTestId(`portfolio-detail-section-${section}`)).toBeInTheDocument();
    expect(getAssessment).toHaveBeenCalledWith('a-1');
  });

  it('zeigt Lesenden im Upload-Schritt kein Upload-Panel', async () => {
    getAssessment.mockResolvedValue(assessment('uploading', null));
    renderPage();
    expect(
      await screen.findByText(/Das Portfolio wurde noch nicht hochgeladen/),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-ingestion-panel')).not.toBeInTheDocument();
  });

  it('übersetzt die Meldungen eines fehlgeschlagenen Jobs', async () => {
    getAssessment.mockResolvedValue(
      assessment('failed', {
        id: 'job-1',
        job_type: 'ingest',
        created_at: null,
        started_at: null,
        finished_at: null,
        status: 'failed',
        files_total: null,
        files_done: 0,
        error_log: [
          { code: 'portfolio_ingestion_corrupt_archive', reason: 'Bad zip file' },
          { code: 'portfolio_unknown_future_code', reason: 'Etwas Neues' },
        ],
      }),
    );
    renderPage();
    expect(
      await screen.findByText('Das Archiv ist beschädigt oder keine gültige ZIP-Datei.'),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Bad zip file/)).not.toBeInTheDocument();
    expect(
      screen.getByText('Unbekannte Meldung des Hintergrund-Auftrags: Etwas Neues'),
    ).toBeInTheDocument();
    expect(screen.getByText('Fehlgeschlagen', { selector: '.MuiChip-label' })).toBeInTheDocument();
  });

  it('zeigt bei einem laufenden Job Fortschritt und «läuft seit mindestens …»', async () => {
    getAssessment.mockResolvedValue(
      assessment('uploading', {
        id: 'job-1',
        job_type: 'ingest',
        created_at: null,
        started_at: null,
        finished_at: null,
        status: 'running',
        files_total: 10,
        files_done: 4,
        error_log: null,
      }),
    );
    renderPage();
    expect(await screen.findByText('4 von 10 Dateien')).toBeInTheDocument();
    expect(screen.getByText(/^läuft seit mindestens \d+ Sek\.$/)).toBeInTheDocument();
    expect(screen.queryByText(/läuft ungewöhnlich lange/)).not.toBeInTheDocument();
  });

  it('warnt bei einem Job, der seit über 20 Minuten läuft', async () => {
    const startedAt = new Date(Date.now() - 95 * 60 * 1000).toISOString();
    getAssessment.mockResolvedValue(
      assessment('grading', {
        id: 'job-1',
        job_type: 'ingest',
        created_at: null,
        finished_at: null,
        status: 'running',
        files_total: null,
        files_done: 0,
        error_log: null,
        started_at: startedAt,
      }),
    );
    renderPage();
    expect(await screen.findByText('läuft seit 1 Std. 35 Min.')).toBeInTheDocument();
    expect(screen.getByText(/läuft ungewöhnlich lange/)).toBeInTheDocument();
  });

  it.each([
    [19, false],
    [21, true],
  ])('warnt nach %i Minuten: %s', async (minutes, warns) => {
    getAssessment.mockResolvedValue(assessment('grading', job({ started_at: minutesAgo(minutes) })));
    renderPage();
    expect(await screen.findByText(`läuft seit ${minutes} Min.`)).toBeInTheDocument();
    expect(!!screen.queryByText(/läuft ungewöhnlich lange/)).toBe(warns);
  });

  it.each<['completed' | 'failed']>([['completed'], ['failed']])(
    'zeigt bei einem Job im Status %s weder «läuft seit» noch die Warnung',
    async (status) => {
      getAssessment.mockResolvedValue(
        assessment('classifying', job({ status, started_at: minutesAgo(95) })),
      );
      renderPage();
      expect(await screen.findByTestId('portfolio-job-status')).toBeInTheDocument();
      expect(screen.queryByText(/läuft seit/)).not.toBeInTheDocument();
      expect(screen.queryByText(/läuft ungewöhnlich lange/)).not.toBeInTheDocument();
    },
  );

  it('listet die betroffenen Dateien unter einer Warnung auf', async () => {
    getAssessment.mockResolvedValue(
      assessment('grading', job({
        status: 'completed',
        error_log: [
          { code: 'portfolio_grading_documents_without_text', paths: ['bilder/scan.png', 'plan.pdf'] },
        ],
      })),
    );
    renderPage();
    expect(await screen.findByText('bilder/scan.png')).toBeInTheDocument();
    expect(screen.getByText('plan.pdf')).toBeInTheDocument();
  });

  it('zeigt bei einem unbekannten Status einen Hinweis statt einer leeren Seite', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    getAssessment.mockResolvedValue(
      assessment('archived' as PortfolioAssessmentStatus, job({ status: 'completed' })),
    );
    renderPage();
    expect(await screen.findByText(/Unbekannter Status «archived»/)).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-job-status')).toBeInTheDocument();
    warn.mockRestore();
  });

  it('markiert nach der vollständigen Überprüfung alle Schritte als erledigt', async () => {
    getAssessment.mockResolvedValue({
      ...assessment('completed', null),
      review_status: 'fully_reviewed',
    });
    renderPage();
    await screen.findByTestId('portfolio-detail-section-review');
    // MUI renders a check icon instead of the step number for completed steps.
    expect(screen.getAllByTestId('CheckCircleIcon')).toHaveLength(4);
  });

  it('behält nach einem gescheiterten Poll den Stand und bietet «Erneut versuchen»', async () => {
    getAssessment
      .mockResolvedValueOnce(assessment('grading', job()))
      .mockRejectedValueOnce(new AppError('portfolio_assessment_load_failed', 'bad gateway', 502))
      .mockResolvedValue(assessment('grading', job({ status: 'completed' })));
    renderPage();
    // Real timers: the first poll fires after PORTFOLIO_POLL_INTERVAL_MS.
    expect(
      await screen.findByText(/möglicherweise veraltet/, {}, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-detail-section-grading')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Erneut versuchen' }));
    await waitFor(() => expect(screen.queryByText(/möglicherweise veraltet/)).not.toBeInTheDocument());
    expect(getAssessment).toHaveBeenCalledTimes(3);
  });

  it('zeigt einen übersetzten Fehler, wenn das Laden scheitert', async () => {
    getAssessment.mockRejectedValue(new AppError('portfolio_assessment_not_found', 'x', 404));
    renderPage();
    expect(await screen.findByText('Portfolio-Bewertung nicht gefunden.')).toBeInTheDocument();
  });
});
