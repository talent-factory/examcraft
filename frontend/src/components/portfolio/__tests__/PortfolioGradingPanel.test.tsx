/**
 * Grading step of the detail page (TF-991): start, resume after a failed run,
 * 409/503 refusals, read-only viewers, and the phase results under the
 * «KI-Vorschlag – nicht final» marking.
 */
import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
  PortfolioPhaseResultCompleted,
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
    approvePhaseResult: jest.fn(),
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

    fireEvent.click(
      await screen.findByRole('button', { name: 'Kriterien und Begründungen anzeigen' }),
    );
    expect(screen.getByText('Zeitplan')).toBeInTheDocument();
    expect(screen.getByText(/Verwaltungsrecht/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Bewertung/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Übernehmen' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Anpassen' })).not.toBeInTheDocument();
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
    expect(screen.queryByText(/5\.0/)).not.toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-aggregate-grade')).not.toBeInTheDocument();
    expect(screen.getByTestId('portfolio-aggregate-provisional')).toHaveTextContent(
      'Vorläufig – KI-Vorschlag, nicht final',
    );
    expect(screen.queryByRole('button', { name: /Bewertung/ })).not.toBeInTheDocument();
  });

  it('zeigt die Ergebnisse auch, wenn das Template nicht lädt', async () => {
    api.getTemplate.mockRejectedValue(new AppError('portfolio_template_load_failed', 'x', 500));
    api.getAssessment.mockResolvedValue(
      assessment('grading', { phase_results: [completedPlanning] }),
    );
    renderPage();

    expect(await screen.findByText(/Das Template konnte nicht geladen werden/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Kriterien und Begründungen anzeigen' }));
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

describe('PortfolioGradingPanel – Review und Noten-Gate (TF-992)', () => {
  const completedRealisation: PortfolioPhaseResult = {
    ...completedPlanning,
    id: 'pr-2',
    phase_id: 'p-2',
    criterion_results: [
      {
        criterion_id: 'c-2',
        score: 2,
        rationale: 'Solide umgesetzt.',
        checklist: {},
        strengths: [],
        improvements: [],
      },
    ],
    total_points: 2,
    max_points: 3,
  };

  function reviewed(result: PortfolioPhaseResult): PortfolioPhaseResult {
    if (result.status !== 'completed') throw new Error('fixture');
    return { ...result, review_status: 'approved', reviewer_id: 1, reviewed_at: '2026-10-01T08:00:00' };
  }

  function expandPhase(phaseId: string) {
    const card = screen.getByTestId(`portfolio-phase-result-${phaseId}`);
    fireEvent.click(
      within(card).getByRole('button', { name: 'Kriterien und Begründungen anzeigen' }),
    );
    return card;
  }

  it('zeigt bei partially_reviewed keine Note, auch wenn die Daten eine enthielten', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('completed', {
        grading_scheme_id: 3,
        review_status: 'partially_reviewed',
        phase_results: [reviewed(completedPlanning), completedRealisation],
        overall_points_awarded: 3,
        overall_points_max: 5,
        overall_percentage: 60,
        // Defensive: the backend never sends this before `fully_reviewed`.
        overall_grade: '4.5',
      }),
    );
    renderPage();

    const aggregate = await screen.findByTestId('portfolio-aggregate');
    expect(within(aggregate).getByText('3 / 5 Punkte · 60 %')).toBeInTheDocument();
    expect(within(aggregate).getByText('1 von 2 Phasen überprüft')).toBeInTheDocument();
    expect(within(aggregate).getByText('Vorläufig – KI-Vorschlag')).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-aggregate-provisional')).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-aggregate-grade')).not.toBeInTheDocument();
    expect(screen.queryByText(/4\.5/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Note:/)).not.toBeInTheDocument();
    // Nothing claims to be final before the gate.
    expect(screen.queryByText(/(?<!nicht )final/i)).not.toBeInTheDocument();
  });

  it('zeigt die Note erst bei fully_reviewed', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('completed', {
        grading_scheme_id: 3,
        review_status: 'fully_reviewed',
        phase_results: [reviewed(completedPlanning), reviewed(completedRealisation)],
        overall_points_awarded: 3,
        overall_points_max: 5,
        overall_percentage: 60,
        overall_grade: '4.5',
      }),
    );
    renderPage();

    expect(await screen.findByTestId('portfolio-aggregate-grade')).toHaveTextContent('Note: 4.5');
    expect(screen.getByText('Alle Phasen überprüft')).toBeInTheDocument();
    expect(screen.getByText('2 von 2 Phasen überprüft')).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-aggregate-provisional')).not.toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-grading-ai-notice')).not.toBeInTheDocument();
  });

  it('erklärt bei fully_reviewed ohne Notenschema, warum keine Note erscheint', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('completed', {
        review_status: 'fully_reviewed',
        phase_results: [reviewed(completedPlanning)],
        overall_points_awarded: 1,
        overall_points_max: 2,
        overall_percentage: 50,
      }),
    );
    renderPage();

    expect(await screen.findByText(/kein Notenschema hinterlegt/)).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-aggregate-grade')).not.toBeInTheDocument();
  });

  it('übernimmt das Aggregat aus der Approve-Antwort ohne erneuten GET', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('completed', {
        grading_scheme_id: 3,
        phase_results: [completedPlanning, completedRealisation],
        overall_points_awarded: 3,
        overall_points_max: 5,
        overall_percentage: 60,
      }),
    );
    api.approvePhaseResult.mockResolvedValue({
      ...(reviewed(completedPlanning) as PortfolioPhaseResultCompleted),
      assessment: {
        review_status: 'partially_reviewed',
        overall_points_awarded: 3,
        overall_points_max: 5,
        overall_percentage: 60,
      },
    });
    renderPage();

    // The cards wait for the template.
    await screen.findByTestId('portfolio-phase-result-p-1');
    expect(screen.getByText('0 von 2 Phasen überprüft')).toBeInTheDocument();
    const planning = expandPhase('p-1');
    fireEvent.click(within(planning).getByRole('button', { name: 'Übernehmen' }));

    expect(await screen.findByText('1 von 2 Phasen überprüft')).toBeInTheDocument();
    expect(within(planning).getByText('Von Lehrperson übernommen')).toBeInTheDocument();
    expect(api.approvePhaseResult).toHaveBeenCalledWith('a-1', 'pr-1');
    expect(api.getAssessment).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId('portfolio-aggregate-grade')).not.toBeInTheDocument();
  });

  it('lädt die Note nach, sobald die letzte Phase übernommen ist', async () => {
    const before = assessment('completed', {
      grading_scheme_id: 3,
      review_status: 'partially_reviewed',
      phase_results: [reviewed(completedPlanning), completedRealisation],
      overall_points_awarded: 3,
      overall_points_max: 5,
      overall_percentage: 60,
    });
    api.getAssessment.mockResolvedValueOnce(before).mockResolvedValue({
      ...before,
      review_status: 'fully_reviewed',
      phase_results: [reviewed(completedPlanning), reviewed(completedRealisation)],
      overall_grade: '4.5',
    });
    api.approvePhaseResult.mockResolvedValue({
      ...(reviewed(completedRealisation) as PortfolioPhaseResultCompleted),
      assessment: {
        review_status: 'fully_reviewed',
        overall_points_awarded: 3,
        overall_points_max: 5,
        overall_percentage: 60,
      },
    });
    renderPage();

    // The cards wait for the template.
    await screen.findByTestId('portfolio-phase-result-p-1');
    fireEvent.click(within(expandPhase('p-2')).getByRole('button', { name: 'Übernehmen' }));

    expect(await screen.findByTestId('portfolio-aggregate-grade')).toHaveTextContent('Note: 4.5');
    expect(api.getAssessment).toHaveBeenCalledTimes(2);
  });

  it('bietet kein «Alle übernehmen» an', async () => {
    api.getAssessment.mockResolvedValue(
      assessment('completed', {
        phase_results: [completedPlanning, completedRealisation],
        overall_points_awarded: 3,
        overall_points_max: 5,
      }),
    );
    renderPage();

    // The cards wait for the template.
    await screen.findByTestId('portfolio-phase-result-p-1');
    expect(screen.queryByRole('button', { name: /übernehmen/i })).not.toBeInTheDocument();
    expandPhase('p-1');
    expandPhase('p-2');
    expect(screen.getAllByRole('button', { name: 'Übernehmen' })).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /alle/i })).not.toBeInTheDocument();
  });
});
