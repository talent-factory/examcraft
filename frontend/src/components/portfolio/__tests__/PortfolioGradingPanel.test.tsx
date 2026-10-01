/**
 * Grading step of the detail page (TF-991): start, resume after a failed run,
 * 409/503 refusals, read-only viewers, and the phase results under the
 * «KI-Vorschlag – nicht final» marking.
 */
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PortfolioAssessmentDetailPage from '../../../pages/portfolio/PortfolioAssessmentDetailPage';
import { portfolioApi } from '../../../api/portfolioApi';
import { AppError } from '../../../errors';
import type {
  PortfolioAssessmentDetail,
  PortfolioAssessmentJob,
  PortfolioAssessmentStatus,
  PortfolioPhaseResult,
  PortfolioTemplate,
} from '../../../types/portfolio';

jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ tier: 'professional', isLoading: false }),
}));

let mockCanManage = true;
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1 },
    hasPermission: (p: string) => mockCanManage && p === 'portfolio_assessments:manage',
  }),
}));

jest.mock('../../../api/portfolioApi', () => ({
  portfolioApi: {
    getAssessment: jest.fn(),
    getTemplate: jest.fn(),
    startGrading: jest.fn(),
  },
}));

const api = portfolioApi as jest.Mocked<typeof portfolioApi>;

function job(overrides: Partial<PortfolioAssessmentJob> = {}): PortfolioAssessmentJob {
  return {
    id: 'job-1',
    job_type: 'grade',
    status: 'queued',
    files_total: null,
    files_done: 0,
    error_log: null,
    created_at: new Date().toISOString(),
    started_at: null,
    finished_at: null,
    ...overrides,
  };
}

function assessment(
  status: PortfolioAssessmentStatus,
  overrides: Partial<PortfolioAssessmentDetail> = {},
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
    job: null,
    documents: [],
    phase_results: [],
    overall_grade: null,
    ...overrides,
  };
}

const template: PortfolioTemplate = {
  id: 't-1',
  name: 'IPA',
  description: null,
  visibility: 'private',
  org_unit_id: null,
  institution_id: 1,
  created_by: 1,
  version: 1,
  is_active: true,
  created_at: null,
  updated_at: null,
  phases: [
    {
      id: 'p-2',
      position: 2,
      name: 'Realisierung',
      description: null,
      expected_folder_patterns: null,
      criteria: [
        {
          id: 'c-2',
          position: 1,
          name: 'Umsetzung',
          type_tag: null,
          max_points: 3,
          rubric_by_score: { '0': 'fehlt', '1': 'schwach', '2': 'solide', '3': 'sehr gut' },
          checklist_items: null,
        },
      ],
    },
    {
      id: 'p-1',
      position: 1,
      name: 'Planung',
      description: null,
      expected_folder_patterns: null,
      criteria: [
        {
          id: 'c-1',
          position: 1,
          name: 'Zeitplan',
          type_tag: null,
          max_points: 2,
          rubric_by_score: { '0': 'kein Plan', '1': 'lückenhaft', '2': 'vollständig' },
          checklist_items: ['Meilensteine'],
        },
      ],
    },
  ],
};

const completedPlanning: PortfolioPhaseResult = {
  id: 'pr-1',
  phase_id: 'p-1',
  status: 'completed',
  criterion_results: [
    {
      criterion_id: 'c-1',
      score: 1,
      rationale: 'Der Zeitplan nennt keine Pufferzeiten.',
      checklist: { Meilensteine: true },
      strengths: ['Klare Etappen'],
      improvements: ['Puffer einplanen'],
    },
  ],
  total_points: 1,
  max_points: 2,
  review_status: 'proposed',
  warnings: null,
  reviewer_id: null,
  reviewer_note: null,
  reviewed_at: null,
  generated_at: null,
};

const failedRealisation: PortfolioPhaseResult = {
  id: 'pr-2',
  phase_id: 'p-2',
  status: 'failed',
  criterion_results: null,
  total_points: null,
  max_points: null,
  review_status: null,
  warnings: null,
  reviewer_id: null,
  reviewer_note: null,
  reviewed_at: null,
  generated_at: null,
};

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
  jest.resetAllMocks();
  mockCanManage = true;
  api.getTemplate.mockResolvedValue(template);
});

describe('PortfolioGradingPanel', () => {
  it('startet die Bewertung bei ready_to_grade und pollt danach', async () => {
    api.getAssessment
      .mockResolvedValueOnce(assessment('ready_to_grade'))
      .mockResolvedValue(assessment('grading', { job: job({ status: 'running' }) }));
    api.startGrading.mockResolvedValue(assessment('grading', { job: job() }));
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Bewertung starten' }));

    await waitFor(() => expect(api.startGrading).toHaveBeenCalledWith('a-1'));
    expect(await screen.findByText('Läuft', { selector: '.MuiChip-label' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Bewertung (starten|fortsetzen)/ })).not.toBeInTheDocument();
  });

  it('bietet nach einer fehlgeschlagenen Phase «Bewertung fortsetzen» an', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('grading', {
        job: job({
          status: 'failed',
          error_log: [{ code: 'portfolio_grading_phase_failed', phase_id: 'p-2' }],
        }),
        phase_results: [completedPlanning, failedRealisation],
      }),
    );
    api.startGrading.mockResolvedValue(assessment('grading', { job: job() }));
    renderPage();

    expect(await screen.findByTestId('portfolio-grading-resumable')).toBeInTheDocument();
    expect(await screen.findByText(/Die Bewertung dieser Phase ist fehlgeschlagen/)).toBeInTheDocument();
    expect(screen.getByText('1 von 2 Phasen bewertet')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Bewertung fortsetzen' }));
    await waitFor(() => expect(api.startGrading).toHaveBeenCalledWith('a-1'));
  });

  it.each([
    [
      409,
      new AppError('portfolio_assessment_grading_already_in_progress', 'x', 409),
      'Für diese Portfolio-Bewertung läuft bereits eine Bewertung.',
    ],
    [
      503,
      new AppError('portfolio_assessment_grading_queue_unavailable', 'x', 503),
      /der Hintergrund-Dienst war nicht erreichbar/,
    ],
  ])('zeigt eine Ablehnung mit Status %i übersetzt an', async (_status, error, text) => {
    api.getAssessment.mockResolvedValue(assessment('ready_to_grade'));
    api.startGrading.mockRejectedValue(error);
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Bewertung starten' }));

    expect(await screen.findByText(text)).toBeInTheDocument();
    // Reloads so a job started elsewhere or failed by the 503 shows up.
    await waitFor(() => expect(api.getAssessment).toHaveBeenCalledTimes(2));
  });

  it('zeigt Lesenden keinen Start-Button, aber die Ergebnisse', async () => {
    mockCanManage = false;
    api.getAssessment.mockResolvedValue(
      assessment('grading', { phase_results: [completedPlanning, failedRealisation] }),
    );
    renderPage();

    expect(await screen.findByText('Zeitplan')).toBeInTheDocument();
    expect(screen.getByText(/Verwaltungsrecht/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Bewertung/ })).not.toBeInTheDocument();
  });

  it('zeigt während einer laufenden Bewertung keinen Start-Button', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('grading', { job: job({ status: 'running' }) }),
    );
    renderPage();

    expect(await screen.findByTestId('portfolio-grading-panel')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Bewertung/ })).not.toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-grading-resumable')).not.toBeInTheDocument();
  });

  it('ordnet die Phasen nach Template und kennzeichnet sie als KI-Vorschlag ohne Note', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('completed', {
        job: job({ status: 'completed' }),
        phase_results: [
          { ...failedRealisation, status: 'pending' },
          completedPlanning,
        ],
        // Even if the backend sent a grade, this view must not show it.
        overall_grade: '5.0',
        overall_points_awarded: 1,
        overall_points_max: 5,
      }),
    );
    renderPage();

    const planning = await screen.findByTestId('portfolio-phase-result-p-1');
    const realisation = screen.getByTestId('portfolio-phase-result-p-2');
    // eslint-disable-next-line no-bitwise
    expect(planning.compareDocumentPosition(realisation) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByTestId('portfolio-grading-ai-notice')).toHaveTextContent(
      'KI-Vorschlag – nicht final',
    );
    expect(screen.queryByText('5.0')).not.toBeInTheDocument();
    expect(screen.queryByText(/Note/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Bewertung/ })).not.toBeInTheDocument();
  });

  it('zeigt die Ergebnisse auch, wenn das Template nicht lädt', async () => {
    api.getTemplate.mockRejectedValue(new AppError('portfolio_template_load_failed', 'x', 500));
    api.getAssessment.mockResolvedValue(
      assessment('grading', { phase_results: [completedPlanning] }),
    );
    renderPage();

    expect(await screen.findByText(/Das Template konnte nicht geladen werden/)).toBeInTheDocument();
    expect(screen.getByText('Unbekannte Phase')).toBeInTheDocument();
    expect(screen.getByText('Unbekanntes Kriterium')).toBeInTheDocument();
    expect(screen.getByText('Punkte: 1')).toBeInTheDocument();
    expect(screen.getByText('Der Zeitplan nennt keine Pufferzeiten.')).toBeInTheDocument();
  });

  it('zeigt den KI-Hinweis nicht mehr, wenn alle bewerteten Phasen überprüft sind', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('completed', {
        phase_results: [{ ...completedPlanning, review_status: 'approved' }],
      }),
    );
    renderPage();

    expect(await screen.findByText('Von Lehrperson übernommen')).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-grading-ai-notice')).not.toBeInTheDocument();
  });

  it('zeigt bei einer Tier-Ablehnung den Upgrade-Hinweis', async () => {
    api.getAssessment.mockResolvedValue(assessment('ready_to_grade'));
    api.startGrading.mockRejectedValue(
      new AppError('portfolio_assessment_tier_insufficient', 'x', 403),
    );
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: 'Bewertung starten' }));

    expect(await screen.findByText('Benötigter Tarif')).toBeInTheDocument();
  });
});
