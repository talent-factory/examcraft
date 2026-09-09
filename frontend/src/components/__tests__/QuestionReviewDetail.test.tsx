/**
 * QuestionReviewDetail tests.
 *
 * TF-772 PR 3: all five catch blocks (load, save, approve, reject, add
 * comment) migrated to `translateError`. This component had no test file at
 * all, so the migration went live with zero coverage of any of its five
 * error paths — these tests pin that behaviour.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionReviewDetail from '../QuestionReviewDetail';
import { ReviewService } from '../../services/ReviewService';
import { AppError } from '../../errors';
import { ReviewStatus } from '../../types/review';

jest.mock('../../services/ReviewService', () => ({
  ReviewService: {
    getQuestionDetail: jest.fn(),
    getComments: jest.fn(),
    editQuestion: jest.fn(),
    approveQuestion: jest.fn(),
    rejectQuestion: jest.fn(),
    addComment: jest.fn(),
  },
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({ id: '42' }),
  useNavigate: () => jest.fn(),
}));

const mockCurrentUser = { id: 1 };
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockCurrentUser }),
}));

jest.mock('react-i18next', () => {
  // A mock that echoes every key would send every AppError down the fallback
  // branch and make the translated-text assertion below silently vacuous —
  // resolve the real errors.* block, same as the sibling admin dialog tests.
  //
  // `t` must stay referentially stable across calls: `loadQuestion` is a
  // useCallback([id, t]), and an unstable mock `t` re-triggers its effect on
  // every render — an infinite load->render->reload loop that never settles.
  const de = require('../../locales/de/translation.json');
  const t = (key: string) =>
    key.startsWith('errors.') ? (de.errors[key.slice('errors.'.length)] ?? key) : key;
  return {
    useTranslation: () => ({ t, i18n: { language: 'de' } }),
  };
});

const mockQuestion = {
  id: 42,
  question_type: 'multiple_choice',
  question_text: 'Was ist 1+1?',
  correct_answer: '2',
  explanation: 'Grundrechenart',
  difficulty: 'medium',
  review_status: ReviewStatus.IN_REVIEW,
  reviewed_by: 1, // matches mockCurrentUser.id, so isReviewer is true and the action buttons render
  tags: [],
};

describe('QuestionReviewDetail', () => {
  beforeEach(() => {
    (ReviewService.getComments as jest.Mock).mockResolvedValue([]);
  });

  it('shows the translated message when getQuestionDetail rejects with a specific code', async () => {
    (ReviewService.getQuestionDetail as jest.Mock).mockRejectedValue(
      new AppError('review_fetch_question_failed', 'Question could not be loaded', 404),
    );

    render(<QuestionReviewDetail />);

    expect(
      await screen.findByText('Frage konnte nicht geladen werden'),
    ).toBeInTheDocument();
  });

  it('shows the translated message when editQuestion (save) rejects with a specific code', async () => {
    (ReviewService.getQuestionDetail as jest.Mock).mockResolvedValue(mockQuestion);
    (ReviewService.editQuestion as jest.Mock).mockRejectedValue(
      new AppError('review_edit_failed', 'Question could not be edited', 500),
    );

    render(<QuestionReviewDetail />);
    fireEvent.click(await screen.findByText('components.questionDetail.save'));

    expect(
      await screen.findByText('Frage konnte nicht bearbeitet werden'),
    ).toBeInTheDocument();
  });

  it('shows the translated message when approveQuestion rejects with a specific code', async () => {
    (ReviewService.getQuestionDetail as jest.Mock).mockResolvedValue(mockQuestion);
    (ReviewService.approveQuestion as jest.Mock).mockRejectedValue(
      new AppError('review_approve_failed', 'Question could not be approved', 500),
    );

    render(<QuestionReviewDetail />);
    fireEvent.click(await screen.findByText('components.questionCard.approveBtn'));

    expect(
      await screen.findByText('Frage konnte nicht genehmigt werden'),
    ).toBeInTheDocument();
  });

  it('shows the translated message when rejectQuestion rejects with a specific code', async () => {
    (ReviewService.getQuestionDetail as jest.Mock).mockResolvedValue(mockQuestion);
    (ReviewService.rejectQuestion as jest.Mock).mockRejectedValue(
      new AppError('review_reject_failed', 'Question could not be rejected', 500),
    );

    render(<QuestionReviewDetail />);
    fireEvent.click(await screen.findByText('components.questionCard.rejectBtn'));

    expect(
      await screen.findByText('Frage konnte nicht abgelehnt werden'),
    ).toBeInTheDocument();
  });

  it('shows the fallback banner when addComment rejects without a specific code', async () => {
    (ReviewService.getQuestionDetail as jest.Mock).mockResolvedValue(mockQuestion);
    (ReviewService.addComment as jest.Mock).mockRejectedValue(new Error('network blip'));

    render(<QuestionReviewDetail />);
    const input = await screen.findByPlaceholderText(
      'components.questionDetail.addCommentPlaceholder',
    );
    fireEvent.change(input, { target: { value: 'Bitte nochmal prüfen' } });
    fireEvent.click(screen.getByText('components.questionDetail.send'));

    await waitFor(() => {
      expect(
        screen.getByText('components.questionReviewDetail.errorComment'),
      ).toBeInTheDocument();
    });
  });
});
