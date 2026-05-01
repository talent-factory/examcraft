/**
 * SyncMoodleIdsDialog tests (TF-336 G4 / Subarea D).
 */

import React from 'react';
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import SyncMoodleIdsDialog from '../SyncMoodleIdsDialog';
import { MoodleConnectionsService } from '../../../services/moodleConnectionsService';
import { ApiError } from '../../../services/submissionsService';

jest.mock('../../../services/moodleConnectionsService');

const mocked = MoodleConnectionsService as jest.Mocked<
  typeof MoodleConnectionsService
>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

beforeEach(() => {
  jest.clearAllMocks();
});

describe('SyncMoodleIdsDialog', () => {
  it('submits a quiz_id without question_ids', async () => {
    mocked.syncQuestionIds.mockResolvedValue({
      exam_id: 1,
      moodle_quiz_id: 42,
      moodle_quiz_name: 'Geo Quiz',
      questions: [
        {
          exam_question_id: 100,
          position: 1,
          moodle_slot: 1,
          moodle_question_id: null,
          moodle_quiz_id: 42,
        },
      ],
    });

    render(
      <Wrapper>
        <SyncMoodleIdsDialog open examId={1} onClose={jest.fn()} />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('sync-quiz-id'), {
      target: { value: '42' },
    });
    fireEvent.click(screen.getByTestId('sync-submit'));

    await waitFor(() =>
      expect(mocked.syncQuestionIds).toHaveBeenCalledWith(1, {
        moodle_quiz_id: 42,
        moodle_question_ids: undefined,
      }),
    );
  });

  it('parses comma-separated question_ids', async () => {
    mocked.syncQuestionIds.mockResolvedValue({
      exam_id: 1,
      moodle_quiz_id: 7,
      moodle_quiz_name: null,
      questions: [],
    });

    render(
      <Wrapper>
        <SyncMoodleIdsDialog open examId={1} onClose={jest.fn()} />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('sync-quiz-id'), {
      target: { value: '7' },
    });
    fireEvent.change(screen.getByTestId('sync-question-ids'), {
      target: { value: '9001, 9002, 9003' },
    });
    fireEvent.click(screen.getByTestId('sync-submit'));

    await waitFor(() =>
      expect(mocked.syncQuestionIds).toHaveBeenCalledWith(1, {
        moodle_quiz_id: 7,
        moodle_question_ids: [9001, 9002, 9003],
      }),
    );
  });

  it('shows the not-visible error on 404', async () => {
    mocked.syncQuestionIds.mockRejectedValue(
      new ApiError({
        kind: 'not_found',
        status: 404,
        message: 'not visible',
      }),
    );

    render(
      <Wrapper>
        <SyncMoodleIdsDialog open examId={1} onClose={jest.fn()} />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('sync-quiz-id'), {
      target: { value: '42' },
    });
    fireEvent.click(screen.getByTestId('sync-submit'));

    await waitFor(() => screen.getByTestId('sync-error'));
    expect(screen.getByTestId('sync-error')).toHaveTextContent(
      /nicht sichtbar|not visible/,
    );
  });
});
