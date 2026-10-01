/**
 * Phase card of the grading step (TF-991): criterion details from result and
 * template, translated warnings, failed/running phases, review markers.
 * TF-992: collapsed details, approve only from the expanded card, override
 * dialog with bounds and partial overrides, review info.
 */
import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PortfolioPhaseResultCard, type PortfolioPhaseReviewProps } from '../PortfolioPhaseResultCard';
import { portfolioApi } from '../../../api/portfolioApi';
import { AppError } from '../../../errors';
import type {
  PortfolioPhaseResult,
  PortfolioPhaseResultCompleted,
  PortfolioPhaseReviewResponse,
  PortfolioTemplatePhase,
} from '../../../types/portfolio';

jest.mock('../../../hooks/useFeatures', () => ({
  useFeatures: () => ({ tier: 'professional', isLoading: false }),
}));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1 } }),
}));

jest.mock('../../../api/portfolioApi', () => ({
  portfolioApi: {
    approvePhaseResult: jest.fn(),
    overridePhaseResult: jest.fn(),
  },
}));

const api = portfolioApi as jest.Mocked<typeof portfolioApi>;

function renderCard(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function expand() {
  fireEvent.click(screen.getByRole('button', { name: 'Kriterien und Begründungen anzeigen' }));
}

const phase: PortfolioTemplatePhase = {
  id: 'p-1',
  position: 1,
  name: 'Planung',
  description: null,
  expected_folder_patterns: null,
  criteria: [
    {
      id: 'c-2',
      position: 2,
      name: 'Risikoanalyse',
      type_tag: null,
      max_points: 3,
      rubric_by_score: { '0': 'fehlt', '1': 'oberflächlich', '2': 'solide', '3': 'umfassend' },
      checklist_items: null,
    },
    {
      id: 'c-1',
      position: 1,
      name: 'Zeitplan',
      type_tag: null,
      max_points: 2,
      rubric_by_score: { '0': 'kein Plan', '1': 'lückenhaft', '2': 'vollständig' },
      checklist_items: ['Meilensteine', 'Puffer'],
    },
  ],
};

function completed(overrides: Partial<PortfolioPhaseResultCompleted> = {}): PortfolioPhaseResult {
  return {
    id: 'pr-1',
    phase_id: 'p-1',
    status: 'completed',
    criterion_results: [
      {
        criterion_id: 'c-2',
        score: 2,
        rationale: 'Risiken sind benannt, aber nicht gewichtet.',
        checklist: {},
        strengths: [],
        improvements: ['Eintrittswahrscheinlichkeit ergänzen'],
      },
      {
        criterion_id: 'c-1',
        score: 1,
        rationale: 'Der Zeitplan nennt keine Pufferzeiten.',
        checklist: { Meilensteine: true, Puffer: false },
        strengths: ['Klare Etappen'],
        improvements: ['Puffer einplanen'],
      },
    ],
    total_points: 3,
    max_points: 5,
    review_status: 'proposed',
    warnings: null,
    reviewer_id: null,
    reviewer_note: null,
    reviewed_at: null,
    generated_at: null,
    ...overrides,
  };
}

function pending(status: 'pending' | 'running' | 'failed'): PortfolioPhaseResult {
  return {
    id: 'pr-1',
    phase_id: 'p-1',
    status,
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
}

describe('PortfolioPhaseResultCard', () => {
  it('zeigt pro Kriterium Punkte, Rubrik, Begründung, Checkliste, Stärken und Verbesserungen', () => {
    renderCard(<PortfolioPhaseResultCard result={completed()} phase={phase} />);

    expect(screen.getByText('Planung')).toBeInTheDocument();
    expect(screen.getByText('3 / 5 Punkte')).toBeInTheDocument();
    expect(screen.getByText('KI-Vorschlag – nicht final')).toBeInTheDocument();
    expand();

    const timeline = screen.getByTestId('portfolio-criterion-c-1');
    expect(within(timeline).getByText('Zeitplan')).toBeInTheDocument();
    expect(within(timeline).getByText('1 / 2 Punkte')).toBeInTheDocument();
    expect(within(timeline).getByText('Rubrik für diese Punktzahl: lückenhaft')).toBeInTheDocument();
    expect(within(timeline).getByText('Der Zeitplan nennt keine Pufferzeiten.')).toBeInTheDocument();
    expect(within(timeline).getByTitle('erfüllt')).toBeInTheDocument();
    expect(within(timeline).getByTitle('nicht erfüllt')).toBeInTheDocument();
    expect(within(timeline).getByText('Meilensteine')).toBeInTheDocument();
    expect(within(timeline).getByText('Klare Etappen')).toBeInTheDocument();
    expect(within(timeline).getByText('Puffer einplanen')).toBeInTheDocument();

    const risks = screen.getByTestId('portfolio-criterion-c-2');
    expect(within(risks).getByText('2 / 3 Punkte')).toBeInTheDocument();
    expect(within(risks).getByText('Rubrik für diese Punktzahl: solide')).toBeInTheDocument();
    // Empty lists render no heading.
    expect(within(risks).queryByText('Stärken')).not.toBeInTheDocument();
    expect(within(risks).queryByText('Checkliste')).not.toBeInTheDocument();
  });

  it('ordnet die Kriterien nach Template-Position, unbekannte zuletzt', () => {
    const result = completed();
    if (result.status !== 'completed') throw new Error('fixture');
    result.criterion_results.unshift({
      criterion_id: 'c-gone',
      score: 1,
      rationale: 'Altes Kriterium.',
      checklist: {},
      strengths: [],
      improvements: [],
    });
    renderCard(<PortfolioPhaseResultCard result={result} phase={phase} />);
    expand();

    const ids = screen
      .getAllByTestId(/^portfolio-criterion-/)
      .map((el) => el.getAttribute('data-testid'));
    expect(ids).toEqual([
      'portfolio-criterion-c-1',
      'portfolio-criterion-c-2',
      'portfolio-criterion-c-gone',
    ]);
    expect(screen.getByText('Unbekanntes Kriterium')).toBeInTheDocument();
    expect(screen.getByText('Punkte: 1')).toBeInTheDocument();
  });

  it('übersetzt Phasen-Warnungen und listet die betroffenen Dateien', () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    renderCard(
      <PortfolioPhaseResultCard
        result={completed({
          warnings: [
            {
              scope: 'phase',
              phase_id: 'p-1',
              code: 'portfolio_grading_documents_omitted',
              paths: ['anhang/log.txt'],
            },
            { scope: 'phase', phase_id: 'p-1', code: 'portfolio_grading_documents_without_text', paths: ['scan.png'] },
            { scope: 'phase', phase_id: 'p-1', code: 'portfolio_grading_phase_without_documents' },
            { code: 'portfolio_grading_future_code', reason: 'Neu' },
          ],
        })}
        phase={phase}
      />,
    );

    expect(screen.getByText(/wegen ihres Umfangs nicht in die Bewertung einbezogen/)).toBeInTheDocument();
    expect(screen.getByText('anhang/log.txt')).toBeInTheDocument();
    expect(screen.getByText(/konnte kein Text gelesen werden/)).toBeInTheDocument();
    expect(screen.getByText('scan.png')).toBeInTheDocument();
    expect(screen.getByText(/keine Datei zugeordnet/)).toBeInTheDocument();
    expect(screen.getByText('Unbekannte Meldung des Hintergrund-Auftrags: Neu')).toBeInTheDocument();
    warn.mockRestore();
  });

  it('kennzeichnet eine fehlgeschlagene Phase als fortsetzbar und zeigt keine Punkte', () => {
    renderCard(<PortfolioPhaseResultCard result={pending('failed')} phase={phase} />);

    expect(screen.getByText('Fehlgeschlagen', { selector: '.MuiChip-label' })).toBeInTheDocument();
    expect(screen.getByText(/Setze die Bewertung fort/)).toBeInTheDocument();
    expect(screen.queryByText(/Punkte/)).not.toBeInTheDocument();
    expect(screen.queryByText('KI-Vorschlag – nicht final')).not.toBeInTheDocument();
  });

  it.each<['pending' | 'running', string]>([
    ['pending', 'Ausstehend'],
    ['running', 'Wird bewertet'],
  ])('zeigt eine Phase im Status %s mit ihrem Status', (status, label) => {
    renderCard(<PortfolioPhaseResultCard result={pending(status)} phase={phase} />);
    expect(screen.getByText(label, { selector: '.MuiChip-label' })).toBeInTheDocument();
  });

  it('ersetzt nach einer Überprüfung den KI-Hinweis durch den Prüfstatus', () => {
    renderCard(
      <PortfolioPhaseResultCard result={completed({ review_status: 'approved' })} phase={phase} />,
    );
    expect(screen.getByText('Von Lehrperson übernommen')).toBeInTheDocument();
    expect(screen.queryByText('KI-Vorschlag – nicht final')).not.toBeInTheDocument();
  });

  it('kommt ohne Template mit Ersatznamen aus', () => {
    renderCard(<PortfolioPhaseResultCard result={completed()} phase={null} />);
    expand();
    expect(screen.getByText('Unbekannte Phase')).toBeInTheDocument();
    expect(screen.getAllByText('Unbekanntes Kriterium')).toHaveLength(2);
    expect(screen.queryByText(/Rubrik/)).not.toBeInTheDocument();
  });
});

describe('PortfolioPhaseResultCard – Review (TF-992)', () => {
  function reviewProps(): PortfolioPhaseReviewProps & {
    onReviewed: jest.Mock;
    onReviewFailed: jest.Mock;
  } {
    return { assessmentId: 'a-1', onReviewed: jest.fn(), onReviewFailed: jest.fn() };
  }

  function response(
    overrides: Partial<PortfolioPhaseResultCompleted> = {},
  ): PortfolioPhaseReviewResponse {
    return {
      ...(completed({ review_status: 'approved', ...overrides }) as PortfolioPhaseResultCompleted),
      assessment: {
        review_status: 'partially_reviewed',
        overall_points_awarded: 3,
        overall_points_max: 5,
        overall_percentage: 60,
      },
    };
  }

  beforeEach(() => {
    jest.resetAllMocks();
  });

  it('zeigt «Übernehmen» erst in der aufgeklappten Karte und bietet kein «Alle übernehmen»', () => {
    renderCard(<PortfolioPhaseResultCard result={completed()} phase={phase} review={reviewProps()} />);

    expect(screen.queryByRole('button', { name: 'Übernehmen' })).not.toBeInTheDocument();
    expect(screen.queryByTestId('portfolio-criterion-c-1')).not.toBeInTheDocument();
    const toggle = screen.getByRole('button', { name: 'Kriterien und Begründungen anzeigen' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    expand();

    expect(screen.getByTestId('portfolio-criterion-c-1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Übernehmen' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Anpassen' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: /alle/i })).not.toBeInTheDocument();
  });

  it('übernimmt die Phase und reicht die Antwort samt Aggregat weiter', async () => {
    const review = reviewProps();
    const answer = response();
    api.approvePhaseResult.mockResolvedValue(answer);
    renderCard(<PortfolioPhaseResultCard result={completed()} phase={phase} review={review} />);

    expand();
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));

    await waitFor(() => expect(review.onReviewed).toHaveBeenCalled());
    expect(api.approvePhaseResult).toHaveBeenCalledWith('a-1', 'pr-1');
    expect(review.onReviewed.mock.calls[0][0]).toEqual(answer);
  });

  it('zeigt einen 409 «nicht überprüfbar» übersetzt an und lädt neu', async () => {
    const review = reviewProps();
    api.approvePhaseResult.mockRejectedValue(
      new AppError('portfolio_assessment_phase_result_not_reviewable', 'x', 409),
    );
    renderCard(<PortfolioPhaseResultCard result={completed()} phase={phase} review={review} />);

    expand();
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));

    expect(await screen.findByText(/Diese Phase ist noch nicht/)).toBeInTheDocument();
    expect(review.onReviewFailed).toHaveBeenCalled();
    expect(review.onReviewed).not.toHaveBeenCalled();
  });

  it('zeigt Lesenden keine Review-Aktionen', () => {
    renderCard(<PortfolioPhaseResultCard result={completed()} phase={phase} />);
    expand();
    expect(screen.queryByRole('button', { name: 'Übernehmen' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Anpassen' })).not.toBeInTheDocument();
  });

  it('bietet nach einer Überprüfung nur noch «Anpassen» an und zeigt wer, wann und die Notiz', () => {
    renderCard(
      <PortfolioPhaseResultCard
        result={completed({
          review_status: 'manual_override',
          reviewer_id: 1,
          reviewer_note: 'Puffer doch vorhanden',
          reviewed_at: '2026-10-01T08:30:00',
          criterion_results: [
            {
              criterion_id: 'c-1',
              score: 2,
              rationale: 'Puffer im Anhang.',
              checklist: {},
              strengths: [],
              improvements: [],
              llm_score: 1,
              llm_rationale: 'Der Zeitplan nennt keine Pufferzeiten.',
            },
          ],
        })}
        phase={phase}
        review={reviewProps()}
      />,
    );

    expect(screen.getByText('Von Lehrperson angepasst')).toBeInTheDocument();
    expect(screen.getByText(/^Von dir überprüft am /)).toBeInTheDocument();
    expect(screen.getByText('Notiz: Puffer doch vorhanden')).toBeInTheDocument();

    expand();
    expect(screen.queryByRole('button', { name: 'Übernehmen' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Anpassen' })).toBeEnabled();
    const timeline = screen.getByTestId('portfolio-criterion-c-1');
    expect(within(timeline).getByText('Angepasst (KI-Vorschlag: 1)')).toBeInTheDocument();
    expect(within(timeline).getByText('Ursprüngliche KI-Begründung')).toBeInTheDocument();
    expect(within(timeline).getByText('Der Zeitplan nennt keine Pufferzeiten.')).toBeInTheDocument();
  });

  it('nennt bei fremder Überprüfung keinen Namen', () => {
    renderCard(
      <PortfolioPhaseResultCard
        result={completed({ review_status: 'approved', reviewer_id: 99, reviewed_at: '2026-10-01T08:30:00' })}
        phase={phase}
      />,
    );
    expect(screen.getByText(/^Überprüft am /)).toBeInTheDocument();
    expect(screen.queryByText(/Von dir/)).not.toBeInTheDocument();
  });

  it('sperrt «Anpassen» ohne Template, weil die Punktgrenzen fehlen', () => {
    renderCard(<PortfolioPhaseResultCard result={completed()} phase={null} review={reviewProps()} />);
    expand();
    expect(screen.getByRole('button', { name: 'Anpassen' })).toBeDisabled();
  });

  describe('Anpassen-Dialog', () => {
    function openDialog(review = reviewProps()) {
      renderCard(<PortfolioPhaseResultCard result={completed()} phase={phase} review={review} />);
      expand();
      fireEvent.click(screen.getByRole('button', { name: 'Anpassen' }));
      return { review, dialog: screen.getByRole('dialog') };
    }

    it('prüft die Punktgrenzen je Kriterium und verlangt eine Änderung', () => {
      const { dialog } = openDialog();
      const save = within(dialog).getByRole('button', { name: 'Anpassung speichern' });
      expect(within(dialog).getByTestId('ai-notice-gradingSuggestion')).toBeInTheDocument();
      // Unchanged: nothing to send.
      expect(save).toBeDisabled();
      expect(within(dialog).getByText(/Noch keine Änderung/)).toBeInTheDocument();

      const zeitplan = within(dialog).getByLabelText('Punkte für Zeitplan');
      fireEvent.change(zeitplan, { target: { value: '3' } });
      expect(within(dialog).getByText('Höchstens 2 Punkte.')).toBeInTheDocument();
      expect(save).toBeDisabled();

      fireEvent.change(zeitplan, { target: { value: '1.5' } });
      expect(within(dialog).getByText('Bitte eine ganze Zahl ab 0 eingeben.')).toBeInTheDocument();
      expect(save).toBeDisabled();

      fireEvent.change(zeitplan, { target: { value: '-1' } });
      expect(save).toBeDisabled();

      fireEvent.change(zeitplan, { target: { value: '2' } });
      expect(save).toBeEnabled();
    });

    it('sendet nur geänderte Kriterien und die Notiz', async () => {
      const answer = response({ review_status: 'manual_override' });
      api.overridePhaseResult.mockResolvedValue(answer);
      const { review, dialog } = openDialog();

      fireEvent.change(within(dialog).getByLabelText('Punkte für Zeitplan'), {
        target: { value: '2' },
      });
      fireEvent.change(within(dialog).getByLabelText('Neue Begründung für Risikoanalyse'), {
        target: { value: '  Gewichtung im Anhang.  ' },
      });
      fireEvent.change(within(dialog).getByLabelText('Notiz zur Überprüfung (optional)'), {
        target: { value: 'Anhang berücksichtigt' },
      });
      fireEvent.click(within(dialog).getByRole('button', { name: 'Anpassung speichern' }));

      await waitFor(() => expect(review.onReviewed).toHaveBeenCalledWith(answer));
      expect(api.overridePhaseResult).toHaveBeenCalledWith('a-1', 'pr-1', {
        overrides: [
          { criterion_id: 'c-1', score: 2, rationale: null },
          { criterion_id: 'c-2', score: 2, rationale: 'Gewichtung im Anhang.' },
        ],
        reviewer_note: 'Anhang berücksichtigt',
      });
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    });

    it('behält Eingaben, wenn die Phase im Hintergrund neu geladen wird', () => {
      const client = new QueryClient();
      const review = reviewProps();
      const ui = (result: PortfolioPhaseResult) => (
        <QueryClientProvider client={client}>
          <PortfolioPhaseResultCard result={result} phase={phase} review={review} />
        </QueryClientProvider>
      );
      const { rerender } = render(ui(completed()));
      expand();
      fireEvent.click(screen.getByRole('button', { name: 'Anpassen' }));
      const field = screen.getByLabelText('Punkte für Zeitplan');
      fireEvent.change(field, { target: { value: '2' } });

      // Same data, new object identity, as after a refetch.
      rerender(ui(completed()));

      expect(screen.getByLabelText('Punkte für Zeitplan')).toHaveValue(2);
    });

    it('zeigt einen 422 der API im Dialog an und bleibt offen', async () => {
      api.overridePhaseResult.mockRejectedValue(
        new AppError('portfolio_assessment_phase_result_override_invalid', 'x', 422),
      );
      const { review, dialog } = openDialog();

      fireEvent.change(within(dialog).getByLabelText('Punkte für Zeitplan'), {
        target: { value: '0' },
      });
      fireEvent.click(within(dialog).getByRole('button', { name: 'Anpassung speichern' }));

      expect(await within(dialog).findByText(/Ungültige Kriterien-Überschreibung/)).toBeInTheDocument();
      expect(review.onReviewed).not.toHaveBeenCalled();
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });
});
