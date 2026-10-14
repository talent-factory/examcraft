/**
 * TF-1055: the bulk lock follows what `GET /api/auth/features` returns —
 * real `useFeatures`, mocked endpoint. `tierLocks.test.tsx` covers the other
 * gated actions with the hook mocked.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';

import ReviewQueue from '../ReviewQueue';
import { EvaluationLimits, UserFeatures } from '../../../hooks/useFeatures';
import { GradesService } from '../../../services/gradesService';

jest.mock('../../../services/gradesService');
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1 }, accessToken: 'token-123', isAuthenticated: true }),
}));

const mockGrades = GradesService as jest.Mocked<typeof GradesService>;
const originalFetch = global.fetch;

const limits = (tier: string, reviewBulk: boolean): EvaluationLimits => ({
  tier,
  label: tier,
  exams_per_month: -1,
  submissions_per_exam: -1,
  drivers: ['moodle_json'],
  llm_grading: true,
  class_history_stats: false,
  review_bulk: reviewBulk,
  custom_grading_schemes: false,
  custom_llm_model: false,
});

const featuresResponse = (evaluationLimits: EvaluationLimits): UserFeatures => ({
  subscription_tier: evaluationLimits.tier,
  features: [],
  quotas: { max_documents: 5, max_questions_per_month: 20, max_users: 1 },
  evaluation_limits: evaluationLimits,
});

const mockEndpoint = (body: UserFeatures) => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => body,
  }) as unknown as typeof fetch;
};

const renderQueue = async () => {
  const view = render(
    <MemoryRouter>
      <ReviewQueue examId={1} />
    </MemoryRouter>,
  );
  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  await waitFor(() => expect(screen.queryByRole('progressbar')).not.toBeInTheDocument());
  return view;
};

beforeEach(() => {
  localStorage.clear();
  mockGrades.getReviewQueue.mockResolvedValue({ total: 0, items: [] });
});

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

describe('Bulk-Sperre folgt /api/auth/features', () => {
  it('ändert die Anzeige, wenn der Endpunkt andere Grenzen liefert', async () => {
    mockEndpoint(featuresResponse(limits('starter', false)));
    const { unmount } = await renderQueue();
    await waitFor(() => expect(screen.getByTestId('bulk-apply-threshold')).toBeDisabled());
    expect(screen.getByTestId('bulk-tier-lock')).toBeInTheDocument();
    unmount();

    localStorage.clear();
    mockEndpoint(featuresResponse(limits('professional', true)));
    await renderQueue();
    await waitFor(() => expect(screen.getByTestId('bulk-apply-threshold')).toBeEnabled());
    expect(screen.queryByTestId('bulk-tier-lock')).not.toBeInTheDocument();
  });

  it('lädt neu, wenn der Cache noch einen Eintrag ohne evaluation_limits hält', async () => {
    // Shape cached before TF-1055: still fresh, but without the limits.
    const { evaluation_limits: _dropped, ...legacy } = featuresResponse(limits('starter', false));
    localStorage.setItem(
      'examcraft_user_features',
      JSON.stringify({ data: legacy, timestamp: Date.now() }),
    );
    mockEndpoint(featuresResponse(limits('starter', false)));

    await renderQueue();

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(await screen.findByTestId('bulk-tier-lock')).toBeInTheDocument();
  });

  it('verwendet keinen Cache-Eintrag eines anderen Benutzers', async () => {
    // Shared localStorage after a logout: another user's (Professional) limits must not unlock this user.
    localStorage.setItem(
      'examcraft_user_features',
      JSON.stringify({
        data: featuresResponse(limits('professional', true)),
        userId: 999,
        timestamp: Date.now(),
      }),
    );
    mockEndpoint(featuresResponse(limits('starter', false)));

    await renderQueue();

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(await screen.findByTestId('bulk-tier-lock')).toBeInTheDocument();
  });
});
