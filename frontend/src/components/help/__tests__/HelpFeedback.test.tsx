import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import HelpFeedback from '../HelpFeedback';
import { helpService } from '../../../services/HelpService';
import { AppError } from '../../../errors';

jest.mock('../../../services/HelpService', () => ({
  helpService: {
    submitFeedback: jest.fn(),
  },
}));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ accessToken: 'test-token' }),
}));

const mockedSubmitFeedback = helpService.submitFeedback as jest.Mock;

const renderFeedback = () =>
  render(<HelpFeedback question="Wie exportiere ich?" answer="So." confidence={0.9} route="/exams" />);

// The two thumb buttons are bare icons without an accessible name; the order
// in the DOM is up, then down.
const thumbsUp = () => screen.getAllByRole('button')[0];

describe('HelpFeedback', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    (console.warn as jest.Mock).mockRestore();
  });

  it('thanks the user after a successful submit', async () => {
    mockedSubmitFeedback.mockResolvedValueOnce(undefined);
    renderFeedback();

    fireEvent.click(thumbsUp());

    expect(await screen.findByText('Danke für dein Feedback!')).toBeInTheDocument();
    expect(mockedSubmitFeedback).toHaveBeenCalledWith('test-token', {
      question: 'Wie exportiere ich?',
      answer: 'So.',
      confidence: 0.9,
      rating: 'up',
      route: '/exams',
    });
  });

  it('takes the thanks back and shows the translated reason when the submit fails (TF-996)', async () => {
    mockedSubmitFeedback.mockRejectedValueOnce(new AppError('help_feedback_failed', 'HTTP 500', 500));
    renderFeedback();

    fireEvent.click(thumbsUp());

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Dein Feedback konnte nicht übermittelt werden.'
    );
    expect(screen.getByRole('alert')).not.toHaveTextContent('HTTP 500');
    expect(screen.queryByText('Danke für dein Feedback!')).not.toBeInTheDocument();
    // The buttons are back, so the rating can be sent again.
    expect(screen.getAllByRole('button')).toHaveLength(2);
  });

  it('falls back to the same sentence for an error without a code', async () => {
    mockedSubmitFeedback.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    renderFeedback();

    fireEvent.click(thumbsUp());

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Dein Feedback konnte nicht übermittelt werden.'
    );
  });

  it('clears the error once a retry succeeds', async () => {
    mockedSubmitFeedback
      .mockRejectedValueOnce(new AppError('help_feedback_failed'))
      .mockResolvedValueOnce(undefined);
    renderFeedback();

    fireEvent.click(thumbsUp());
    expect(await screen.findByRole('alert')).toBeInTheDocument();

    fireEvent.click(thumbsUp());
    expect(await screen.findByText('Danke für dein Feedback!')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
