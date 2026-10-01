/**
 * Phase card of the grading step (TF-991): criterion details from result and
 * template, translated warnings, failed/running phases, review markers.
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { PortfolioPhaseResultCard } from '../PortfolioPhaseResultCard';
import type {
  PortfolioPhaseResult,
  PortfolioPhaseResultCompleted,
  PortfolioTemplatePhase,
} from '../../../types/portfolio';

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
    render(<PortfolioPhaseResultCard result={completed()} phase={phase} />);

    expect(screen.getByText('Planung')).toBeInTheDocument();
    expect(screen.getByText('3 / 5 Punkte')).toBeInTheDocument();
    expect(screen.getByText('KI-Vorschlag – nicht final')).toBeInTheDocument();

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
    render(<PortfolioPhaseResultCard result={result} phase={phase} />);

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
    render(
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
    render(<PortfolioPhaseResultCard result={pending('failed')} phase={phase} />);

    expect(screen.getByText('Fehlgeschlagen', { selector: '.MuiChip-label' })).toBeInTheDocument();
    expect(screen.getByText(/Setze die Bewertung fort/)).toBeInTheDocument();
    expect(screen.queryByText(/Punkte/)).not.toBeInTheDocument();
    expect(screen.queryByText('KI-Vorschlag – nicht final')).not.toBeInTheDocument();
  });

  it.each<['pending' | 'running', string]>([
    ['pending', 'Ausstehend'],
    ['running', 'Wird bewertet'],
  ])('zeigt eine Phase im Status %s mit ihrem Status', (status, label) => {
    render(<PortfolioPhaseResultCard result={pending(status)} phase={phase} />);
    expect(screen.getByText(label, { selector: '.MuiChip-label' })).toBeInTheDocument();
  });

  it('ersetzt nach einer Überprüfung den KI-Hinweis durch den Prüfstatus', () => {
    render(
      <PortfolioPhaseResultCard result={completed({ review_status: 'approved' })} phase={phase} />,
    );
    expect(screen.getByText('Von Lehrperson übernommen')).toBeInTheDocument();
    expect(screen.queryByText('KI-Vorschlag – nicht final')).not.toBeInTheDocument();
  });

  it('kommt ohne Template mit Ersatznamen aus', () => {
    render(<PortfolioPhaseResultCard result={completed()} phase={null} />);
    expect(screen.getByText('Unbekannte Phase')).toBeInTheDocument();
    expect(screen.getAllByText('Unbekanntes Kriterium')).toHaveLength(2);
    expect(screen.queryByText(/Rubrik/)).not.toBeInTheDocument();
  });
});
