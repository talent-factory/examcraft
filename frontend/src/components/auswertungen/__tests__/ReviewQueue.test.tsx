/**
 * Tests for ReviewQueue (TF-334).
 *
 * We mock the GradesService — the component logic (filter,
 * selection, approve, override, bulk-approve) is the
 * test subject here.
 */

import React from 'react';
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
} from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import ReviewQueue from '../ReviewQueue';
import { GradesService } from '../../../services/gradesService';
import { ReviewQueue as ReviewQueueData } from '../../../types/submission';

jest.mock('../../../services/gradesService');
const mockGradesService = GradesService as jest.Mocked<typeof GradesService>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const baseQueue: ReviewQueueData = {
  total: 2,
  items: [
    {
      grade_id: 11,
      submission_id: 101,
      student_id: 5,
      student_external_id: 'a@x.org',
      student_display_name: 'Anna',
      exam_question_id: 1001,
      question_id: 901,
      question_text: 'Erkläre Kapselung in OOP.',
      correct_answer: 'Daten + Verhalten in einem Objekt zusammenfassen.',
      explanation: null,
      given_answer: 'Daten und Methoden bündeln.',
      points_awarded: 3.0,
      points_max: 4.0,
      confidence: 0.45,
      rationale: 'Aspekt teilweise erfasst.',
      matched_aspects: ['Daten'],
      missing_aspects: ['Verhalten'],
      status: 'proposed',
    },
    {
      grade_id: 12,
      submission_id: 102,
      student_id: 6,
      student_external_id: 'b@x.org',
      student_display_name: null,
      exam_question_id: 1001,
      question_id: 901,
      question_text: 'Erkläre Kapselung in OOP.',
      correct_answer: 'Daten + Verhalten in einem Objekt zusammenfassen.',
      explanation: null,
      given_answer: '',
      points_awarded: 0.0,
      points_max: 4.0,
      confidence: 0.95,
      rationale: 'Vollständig.',
      matched_aspects: ['Daten', 'Verhalten'],
      missing_aspects: [],
      status: 'proposed',
    },
  ],
};

const renderQueue = (overrides: Partial<React.ComponentProps<typeof ReviewQueue>> = {}) => {
  const onTotalChange = jest.fn();
  render(
    <Wrapper>
      <ReviewQueue examId={42} onTotalChange={onTotalChange} {...overrides} />
    </Wrapper>,
  );
  return { onTotalChange };
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGradesService.getReviewQueue.mockResolvedValue(baseQueue);
});

describe('ReviewQueue', () => {
  it('renders cards with confidence chips and notifies parent of total', async () => {
    const { onTotalChange } = renderQueue();
    await waitFor(() => {
      expect(screen.getByTestId('review-card-11')).toBeInTheDocument();
    });
    expect(screen.getByTestId('review-card-12')).toBeInTheDocument();
    expect(onTotalChange).toHaveBeenCalledWith(2);
    // matched / missing aspects are visible
    expect(screen.getAllByText('Daten').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Verhalten').length).toBeGreaterThan(0);
  });

  it('renders question, model solution, student answer and rationale via MarkdownRenderer (TF-429)', async () => {
    mockGradesService.getReviewQueue.mockResolvedValue({
      total: 1,
      items: [
        {
          ...baseQueue.items[0],
          grade_id: 11,
          question_text: '**Praxisszenario:** Erkläre Kapselung.',
          correct_answer: '**Musterlösung** mit Struktur.',
          given_answer: '1.) Erster Punkt\n2.) Zweiter Punkt',
          rationale: '**Vorschlag:** solide Leistung.',
        },
      ],
    });
    renderQueue();
    await waitFor(() => {
      expect(screen.getByTestId('review-card-11')).toBeInTheDocument();
    });

    // The react-markdown mock renders children verbatim under
    // [data-testid="react-markdown"]. If the raw markdown text shows up
    // there, it proves the field goes through MarkdownRenderer (instead of
    // a bare <Typography>, which shows `**` literally and swallows line
    // breaks).
    const rendered = screen
      .getAllByTestId('react-markdown')
      .map((el) => el.textContent ?? '');
    expect(rendered).toEqual(
      expect.arrayContaining([
        expect.stringContaining('**Praxisszenario:** Erkläre Kapselung.'),
        expect.stringContaining('**Musterlösung** mit Struktur.'),
        expect.stringContaining('1.) Erster Punkt'),
        expect.stringContaining('**Vorschlag:** solide Leistung.'),
      ]),
    );
  });

  it('approves a grade via the approve button', async () => {
    mockGradesService.approve.mockResolvedValue({
      id: 11,
      points_awarded: 3.0,
      points_max: 4.0,
      status: 'approved',
      reviewer_id: 1,
      reviewer_note: null,
      reviewed_at: null,
    });
    renderQueue();
    expect(await screen.findByTestId('approve-11')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('approve-11'));
    await waitFor(() => {
      expect(mockGradesService.approve).toHaveBeenCalledWith(11);
    });
    // Re-fetch after approve (initial + after a successful approve).
    await waitFor(() => {
      expect(mockGradesService.getReviewQueue).toHaveBeenCalledTimes(2);
    });
  });

  it('opens override dialog and submits new points', async () => {
    mockGradesService.override.mockResolvedValue({
      id: 11,
      points_awarded: 4.0,
      points_max: 4.0,
      status: 'manual_override',
      reviewer_id: 1,
      reviewer_note: 'Vollständig erfasst',
      reviewed_at: null,
    });
    renderQueue();
    expect(await screen.findByTestId('override-11')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('override-11'));

    const pointsField = await screen.findByTestId('override-points');
    fireEvent.change(pointsField, { target: { value: '4' } });
    fireEvent.click(screen.getByTestId('override-submit'));

    await waitFor(() => {
      expect(mockGradesService.override).toHaveBeenCalledWith(11, {
        points_awarded: 4,
        reviewer_note: undefined,
      });
    });
  });

  it('bulk-approves selected grades via checkbox selection', async () => {
    mockGradesService.bulkApprove.mockResolvedValue({
      approved_count: 1,
      grade_ids: [11],
    });
    renderQueue();
    expect(await screen.findByTestId('select-11')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('select-11'));
    fireEvent.click(screen.getByTestId('bulk-apply-selection'));

    await waitFor(() => {
      expect(mockGradesService.bulkApprove).toHaveBeenCalledWith({
        examId: 42,
        gradeIds: [11],
      });
    });
  });

  it('bulk-approves by confidence threshold after window.confirm', async () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    mockGradesService.bulkApprove.mockResolvedValue({
      approved_count: 1,
      grade_ids: [12],
    });
    renderQueue();
    expect(
      await screen.findByTestId('bulk-apply-threshold'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('bulk-apply-threshold'));

    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(mockGradesService.bulkApprove).toHaveBeenCalledWith({
        examId: 42,
        confidenceMin: 0.8,
      });
    });
    confirmSpy.mockRestore();
  });

  it('bulk-approve aborts when user cancels the confirm dialog', async () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);
    renderQueue();
    expect(
      await screen.findByTestId('bulk-apply-threshold'),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('bulk-apply-threshold'));
    expect(mockGradesService.bulkApprove).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('renders empty state when queue is empty', async () => {
    mockGradesService.getReviewQueue.mockResolvedValue({ items: [], total: 0 });
    renderQueue();
    await waitFor(() => {
      // Empty hint key lands as a success alert
      const alert = screen.getByRole('alert');
      expect(within(alert).getByText(/keine offenen|no open/i)).toBeInTheDocument();
    });
  });

  it('shows error alert when load fails', async () => {
    mockGradesService.getReviewQueue.mockRejectedValue(
      new Error('Boom'),
    );
    renderQueue();
    await waitFor(() => {
      expect(
        screen.getByText(/Review-Queue konnte nicht|Could not load/i),
      ).toBeInTheDocument();
    });
  });
});
