/**
 * Classification review: grouping, correction, confirm, errors (TF-990).
 */
import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  PortfolioClassificationPanel,
  groupPortfolioDocuments,
} from '../PortfolioClassificationPanel';
import { portfolioApi } from '../../../api/portfolioApi';
import { AppError } from '../../../errors';
import { portfolioAssessmentQueryKey } from '../../../hooks/usePortfolioAssessment';
import type {
  PortfolioAssessmentDetail,
  PortfolioAssessmentJob,
  PortfolioDocument,
  PortfolioTemplate,
  PortfolioTemplatePhase,
} from '../../../types/portfolio';

jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ tier: 'professional', isLoading: false }),
}));

let mockPermissions = new Set<string>(['portfolio_assessments:manage']);
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1 }, hasPermission: (p: string) => mockPermissions.has(p) }),
}));

// The error class stays real: the panel recognises the 409 by its name.
jest.mock('../../../api/portfolioApi', () => {
  const actual = jest.requireActual('../../../api/portfolioApi');
  return {
    ...actual,
    portfolioApi: {
      getTemplate: jest.fn(),
      startClassification: jest.fn(),
      updateDocumentPhase: jest.fn(),
      confirmClassification: jest.fn(),
    },
  };
});

const api = portfolioApi as jest.Mocked<typeof portfolioApi>;
const { PortfolioUnclassifiedDocumentsError } = jest.requireActual('../../../api/portfolioApi');

function phase(id: string, position: number, name: string): PortfolioTemplatePhase {
  return {
    id,
    position,
    name,
    description: null,
    expected_folder_patterns: null,
    criteria: [],
  };
}

const PHASES = [phase('p-2', 1, 'Umsetzung'), phase('p-1', 0, 'Planung'), phase('p-3', 2, 'Reflexion')];

const TEMPLATE: PortfolioTemplate = {
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
  phases: PHASES,
};

function doc(
  id: number,
  path: string,
  overrides: Partial<PortfolioDocument> = {},
): PortfolioDocument {
  return {
    document_id: id,
    original_relative_path: path,
    origin: 'upload_zip',
    phase_id: null,
    classification_confidence: null,
    classification_source: null,
    ...overrides,
  };
}

function assessment(
  documents: PortfolioDocument[],
  job: PortfolioAssessmentJob | null = null,
): PortfolioAssessmentDetail {
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
    job,
    documents,
    phase_results: [],
    overall_grade: null,
  };
}

const PROPOSED = [
  doc(1, 'b/plan.md', { phase_id: 'p-1', classification_confidence: 0.92, classification_source: 'auto' }),
  doc(2, 'a/notizen.txt', { classification_confidence: 0.41 }),
  doc(3, 'code/main.py', {
    origin: 'github_repository',
    phase_id: 'p-2',
    classification_source: 'manual',
  }),
];

function renderPanel(detail: PortfolioAssessmentDetail) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  client.setQueryData(portfolioAssessmentQueryKey(detail.id), detail);
  const view = render(
    <QueryClientProvider client={client}>
      <PortfolioClassificationPanel assessment={detail} />
    </QueryClientProvider>,
  );
  const rerenderFromCache = () =>
    view.rerender(
      <QueryClientProvider client={client}>
        <PortfolioClassificationPanel
          assessment={client.getQueryData(portfolioAssessmentQueryKey(detail.id)) as PortfolioAssessmentDetail}
        />
      </QueryClientProvider>,
    );
  return { client, rerenderFromCache };
}

/**
 * Until the template is loaded, assigned files sit in «Unbekannte Phase»;
 * afterwards they move to their phase and their select is mounted anew.
 */
const templateLoaded = () => screen.findByTestId('portfolio-classification-group-p-1');

beforeEach(() => {
  jest.resetAllMocks();
  mockPermissions = new Set(['portfolio_assessments:manage']);
  api.getTemplate.mockResolvedValue(TEMPLATE);
});

describe('groupPortfolioDocuments', () => {
  it('stellt Dateien ohne Phase voran und ordnet die Phasen nach Position', () => {
    const groups = groupPortfolioDocuments(
      [...PROPOSED, doc(4, 'alt.md', { phase_id: 'p-gone' })],
      PHASES,
    );
    expect(groups.map((g) => g.key)).toEqual(['unassigned', 'p-1', 'p-2', 'p-3', 'unknown']);
    expect(groups[0].documents.map((d) => d.document_id)).toEqual([2]);
    expect(groups[3].documents).toEqual([]);
    expect(groups[4].documents.map((d) => d.document_id)).toEqual([4]);
  });

  it('sortiert innerhalb einer Gruppe nach Pfad und lässt leere Ohne-Phase-Gruppe weg', () => {
    const groups = groupPortfolioDocuments(
      [doc(1, 'z.md', { phase_id: 'p-1' }), doc(2, 'a.md', { phase_id: 'p-1' })],
      PHASES,
    );
    expect(groups[0].key).toBe('p-1');
    expect(groups[0].documents.map((d) => d.original_relative_path)).toEqual(['a.md', 'z.md']);
  });
});

describe('PortfolioClassificationPanel', () => {
  it('zeigt die Dateien gruppiert mit Herkunft, Quelle und Konfidenz', async () => {
    renderPanel(assessment(PROPOSED));
    await templateLoaded();

    const unassigned = screen.getByTestId('portfolio-classification-group-unassigned');
    expect(within(unassigned).getByRole('heading', { name: 'Ohne Phase' })).toBeInTheDocument();
    expect(within(unassigned).getByText('a/notizen.txt')).toBeInTheDocument();
    expect(within(unassigned).getByText('41 %')).toBeInTheDocument();
    expect(within(unassigned).getByText(/Unter 70 %/)).toBeInTheDocument();
    expect(within(unassigned).getByText('Offen')).toBeInTheDocument();

    const planning = screen.getByTestId('portfolio-classification-group-p-1');
    expect(within(planning).getByRole('heading', { name: 'Planung' })).toBeInTheDocument();
    expect(within(planning).getByText('92 %')).toBeInTheDocument();
    expect(within(planning).getByTestId('ai-notice-classificationSuggestion')).toHaveTextContent(
      'KI-Vorschlag – bitte prüfen',
    );

    const implementation = screen.getByTestId('portfolio-classification-group-p-2');
    expect(within(implementation).getByText('GitHub')).toBeInTheDocument();
    expect(within(implementation).getByText('Manuell')).toBeInTheDocument();

    expect(
      within(screen.getByTestId('portfolio-classification-group-p-3')).getByText(
        'Dieser Phase ist keine Datei zugeordnet.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-classification-summary')).toHaveTextContent(
      'Dateien: 3 · ohne Phase: 1',
    );
    // EU AI Act block above the table once there is a proposal.
    expect(screen.getAllByTestId('ai-notice-classificationSuggestion')[0]).toHaveTextContent(
      /KI-System/,
    );
  });

  it('startet die Klassifikation und übernimmt den neuen Job', async () => {
    const queued: PortfolioAssessmentJob = {
      id: 'job-2',
      job_type: 'classify',
      status: 'queued',
      files_total: null,
      files_done: 0,
      error_log: null,
      created_at: null,
      started_at: null,
      finished_at: null,
    };
    const { job: _job, documents: _docs, phase_results: _pr, overall_grade: _g, ...summary } =
      assessment([]);
    api.startClassification.mockResolvedValue({ ...summary, job: queued });
    const { client } = renderPanel(assessment([doc(1, 'x.md')]));

    const start = screen.getByTestId('portfolio-classification-start');
    expect(start).toHaveTextContent('Zuordnung vorschlagen');
    fireEvent.click(start);

    await waitFor(() => expect(api.startClassification).toHaveBeenCalledWith('a-1'));
    await waitFor(() =>
      expect(
        (client.getQueryData(portfolioAssessmentQueryKey('a-1')) as PortfolioAssessmentDetail).job,
      ).toEqual(queued),
    );
  });

  it('kennzeichnet auch eine KI-Ausgabe nur unter dem Schwellwert', async () => {
    renderPanel(assessment([doc(1, 'x.md', { classification_confidence: 0.3 })]));
    expect(await screen.findByTestId('ai-notice-classificationSuggestion')).toHaveTextContent(
      /KI-System/,
    );
  });

  it('zeigt vor einem Vorschlag keinen KI-Hinweis', async () => {
    renderPanel(assessment([doc(1, 'x.md')]));
    await templateLoaded();
    expect(screen.queryByTestId('ai-notice-classificationSuggestion')).not.toBeInTheDocument();
  });

  it('bietet nach einem Vorschlag die erneute Klassifikation mit Hinweis an', async () => {
    renderPanel(assessment(PROPOSED));
    expect(await screen.findByTestId('portfolio-classification-start')).toHaveTextContent(
      'Zuordnung erneut vorschlagen',
    );
    expect(screen.getByText(/Manuell zugeordnete Dateien bleiben/)).toBeInTheDocument();
  });

  it('übersetzt 409 und 503 beim Start', async () => {
    api.startClassification.mockRejectedValueOnce(
      new AppError('portfolio_assessment_classification_already_in_progress', 'x', 409),
    );
    renderPanel(assessment([doc(1, 'x.md')]));
    fireEvent.click(screen.getByTestId('portfolio-classification-start'));
    expect(
      await screen.findByText(/Für diese Portfolio-Bewertung läuft bereits/),
    ).toBeInTheDocument();

    api.startClassification.mockRejectedValueOnce(
      new AppError('portfolio_assessment_classification_queue_unavailable', 'x', 503),
    );
    fireEvent.click(screen.getByTestId('portfolio-classification-start'));
    expect(await screen.findByText(/Die Klassifikation konnte nicht/)).toBeInTheDocument();
  });

  it('korrigiert die Phase einer Datei per PATCH und gruppiert neu', async () => {
    api.updateDocumentPhase.mockResolvedValue({
      ...PROPOSED[1],
      phase_id: 'p-3',
      classification_source: 'manual',
      classification_confidence: null,
    });
    const { client, rerenderFromCache } = renderPanel(assessment(PROPOSED));

    await templateLoaded();
    const select = screen.getByTestId('portfolio-classification-phase-2');
    expect(select).not.toBeDisabled();
    // The empty value is only a placeholder, never a choice.
    expect(within(select).getByText('Phase wählen')).toBeDisabled();
    fireEvent.change(select, { target: { value: 'p-3' } });

    await waitFor(() => expect(api.updateDocumentPhase).toHaveBeenCalledWith('a-1', 2, 'p-3'));
    await waitFor(() =>
      expect(
        (client.getQueryData(portfolioAssessmentQueryKey('a-1')) as PortfolioAssessmentDetail)
          .documents.find((d) => d.document_id === 2)?.phase_id,
      ).toBe('p-3'),
    );
    // The detail page passes the cached assessment down; mimic that.
    rerenderFromCache();
    expect(screen.queryByTestId('portfolio-classification-group-unassigned')).not.toBeInTheDocument();
    expect(
      within(screen.getByTestId('portfolio-classification-group-p-3')).getByText('a/notizen.txt'),
    ).toBeInTheDocument();
  });

  it('zeigt einen Korrekturfehler übersetzt an', async () => {
    api.updateDocumentPhase.mockRejectedValue(
      new AppError('portfolio_assessment_document_invalid_phase', 'x', 422),
    );
    renderPanel(assessment(PROPOSED));
    await templateLoaded();
    const select = screen.getByTestId('portfolio-classification-phase-1');
    expect(select).not.toBeDisabled();
    fireEvent.change(select, { target: { value: 'p-2' } });
    expect(await screen.findByText(/Die gewählte Phase gehört nicht/)).toBeInTheDocument();
  });

  it('sperrt das Bestätigen, solange eine Datei ohne Phase ist', async () => {
    renderPanel(assessment(PROPOSED));
    expect(await screen.findByTestId('portfolio-classification-confirm')).toBeDisabled();
    expect(screen.getByText(/offen: 1/)).toBeInTheDocument();
  });

  it('bestätigt eine vollständige Zuordnung', async () => {
    const complete = PROPOSED.map((d) =>
      d.phase_id ? d : { ...d, phase_id: 'p-3', classification_source: 'manual' as const },
    );
    const { job: _job, documents: _docs, phase_results: _pr, overall_grade: _g, ...summary } =
      assessment(complete);
    api.confirmClassification.mockResolvedValue({ ...summary, status: 'ready_to_grade' });
    const { client } = renderPanel(assessment(complete));

    const confirm = await screen.findByTestId('portfolio-classification-confirm');
    expect(confirm).not.toBeDisabled();
    fireEvent.click(confirm);

    await waitFor(() => expect(api.confirmClassification).toHaveBeenCalledWith('a-1'));
    await waitFor(() =>
      expect(
        (client.getQueryData(portfolioAssessmentQueryKey('a-1')) as PortfolioAssessmentDetail)
          .status,
      ).toBe('ready_to_grade'),
    );
  });

  it('markiert bei 409 die vom Server gemeldeten Dateien ohne Phase', async () => {
    const complete = PROPOSED.map((d) => ({ ...d, phase_id: d.phase_id ?? 'p-3' }));
    api.confirmClassification.mockRejectedValue(
      new PortfolioUnclassifiedDocumentsError(
        new AppError('portfolio_assessment_unclassified_documents', 'x', 409),
        [3],
      ),
    );
    renderPanel(assessment(complete));

    fireEvent.click(await screen.findByTestId('portfolio-classification-confirm'));

    expect(
      await screen.findByText('Es sind noch nicht alle Dateien einer Phase zugeordnet.'),
    ).toBeInTheDocument();
    const row = screen.getByTestId('portfolio-classification-row-3');
    expect(row).toHaveAttribute('data-flagged', 'true');
    expect(within(row).getByText('Beim Bestätigen noch ohne Phase')).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-classification-row-1')).not.toHaveAttribute('data-flagged');

    // Correcting the flagged file clears its mark and the outdated refusal.
    api.updateDocumentPhase.mockResolvedValue({ ...complete[2], phase_id: 'p-1' });
    await templateLoaded();
    fireEvent.change(screen.getByTestId('portfolio-classification-phase-3'), {
      target: { value: 'p-1' },
    });
    await waitFor(() =>
      expect(
        screen.queryByText('Es sind noch nicht alle Dateien einer Phase zugeordnet.'),
      ).not.toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByTestId('portfolio-classification-row-3')).not.toHaveAttribute(
        'data-flagged',
      ),
    );
  });

  it('übersetzt 409 «nicht bereit» beim Bestätigen', async () => {
    const complete = PROPOSED.map((d) => ({ ...d, phase_id: d.phase_id ?? 'p-3' }));
    api.confirmClassification.mockRejectedValue(
      new AppError('portfolio_assessment_classification_not_ready', 'x', 409),
    );
    renderPanel(assessment(complete));
    fireEvent.click(await screen.findByTestId('portfolio-classification-confirm'));
    expect(await screen.findByText(/Diese Portfolio-Bewertung ist/)).toBeInTheDocument();
  });

  it('sperrt Start, Korrektur und Bestätigen, solange die Klassifikation läuft', async () => {
    const running: PortfolioAssessmentJob = {
      id: 'job-2',
      job_type: 'classify',
      status: 'running',
      files_total: 3,
      files_done: 1,
      error_log: null,
      created_at: null,
      started_at: null,
      finished_at: null,
    };
    renderPanel(assessment(PROPOSED, running));
    expect(await screen.findByText(/Die KI ordnet die Dateien gerade zu/)).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-classification-start')).not.toBeInTheDocument();
    expect(screen.getByTestId('portfolio-classification-confirm')).toBeDisabled();
    await templateLoaded();
    expect(screen.getByTestId('portfolio-classification-phase-1')).toBeDisabled();
  });

  it('zeigt Lesenden die Zuordnung ohne Aktionen', async () => {
    mockPermissions = new Set(['portfolio_assessments:read']);
    renderPanel(assessment(PROPOSED));
    expect(await screen.findByText(/eine Lehrperson mit Verwaltungsrecht/)).toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-classification-start')).not.toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-classification-confirm')).not.toBeInTheDocument();
    await templateLoaded();
    expect(screen.getByTestId('portfolio-classification-phase-1')).toBeDisabled();
  });

  it('meldet ein nicht ladbares Template und gruppiert dann unter «Unbekannte Phase»', async () => {
    api.getTemplate.mockRejectedValue(new AppError('portfolio_template_not_found', 'x', 404));
    renderPanel(assessment(PROPOSED));
    expect(
      await screen.findByText(/Die Phasen des Templates konnten nicht geladen werden/),
    ).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-classification-group-unknown')).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-classification-phase-1')).toBeDisabled();
  });

  it('weist auf ein leeres Portfolio hin und sperrt Start und Bestätigen', async () => {
    renderPanel(assessment([]));
    expect(await screen.findByText('Dieses Portfolio enthält keine Dateien.')).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-classification-start')).toBeDisabled();
    expect(screen.getByTestId('portfolio-classification-confirm')).toBeDisabled();
  });
});
