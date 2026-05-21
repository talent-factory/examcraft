/**
 * Tests for the dashboard widget — TF-337 link integration only.
 *
 * The fuller dashboard rendering is covered by component-layer tests
 * (StatsCard, QuickActionCard) and the i18n-keys guard. This file
 * pins the new TF-337 contract: when activities exist, a
 * "view all activities" link routes to /aktivitaeten.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';

import { Dashboard } from '../Dashboard';
import {
  fetchDashboardActivity,
  fetchDashboardStats,
} from '../../api/dashboard';

// date-fns v3+ ships locale/* as ESM, which CRA's Babel transform
// can't parse out of the box. Mocking the locale module sidesteps
// the transform without touching jest config; the page only uses the
// imported objects as opaque tokens passed to formatDistanceToNow.
jest.mock('date-fns/locale', () => ({ de: {}, enUS: {}, fr: {}, it: {} }));
jest.mock('date-fns', () => ({
  formatDistanceToNow: () => 'vor 1 Stunde',
}));

jest.mock('../../api/dashboard', () => ({
  fetchDashboardStats: jest.fn(),
  fetchDashboardActivity: jest.fn(),
}));

// AuthContext: keep it cheap — Dashboard only reads ``user.first_name``.
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { first_name: 'Test' } }),
}));

// Stub the cards so we don't drag MUI / Tailwind concerns into this test.
jest.mock('../../components/cards/QuickActionCard', () => ({
  QuickActionCard: ({ title }: { title: string }) => <div>{title}</div>,
}));
jest.mock('../../components/cards/StatsCard', () => ({
  StatsCard: ({ label }: { label: string }) => <div>{label}</div>,
}));
jest.mock('../../components/auth/EmailVerificationBanner', () => ({
  __esModule: true,
  default: () => null,
}));

const mockStats = fetchDashboardStats as jest.MockedFunction<
  typeof fetchDashboardStats
>;
const mockActivity = fetchDashboardActivity as jest.MockedFunction<
  typeof fetchDashboardActivity
>;

beforeEach(() => {
  jest.clearAllMocks();
  mockStats.mockResolvedValue({
    generated_questions: 1,
    documents: 1,
    validated_questions: 1,
    exams: 1,
  });
});

const renderDashboard = () =>
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );

describe('Dashboard — view-all-activities link (TF-337)', () => {
  test('renders the link to /aktivitaeten when activities exist', async () => {
    mockActivity.mockResolvedValue({
      activities: [
        {
          id: 'doc_1',
          type: 'document_uploaded',
          title: 'doc.pdf',
          timestamp: '2026-05-01T10:00:00Z',
        },
      ],
    });

    renderDashboard();

    const link = await screen.findByTestId('dashboard-view-all-activities');
    expect(link).toHaveAttribute('href', '/aktivitaeten');
  });

  test('omits the link when there is no activity to drill into', async () => {
    mockActivity.mockResolvedValue({ activities: [] });

    renderDashboard();

    // Wait for the "no activity" branch to render before asserting
    // the absence of the link — otherwise we'd race the loading state.
    await waitFor(() => expect(mockActivity).toHaveBeenCalled());
    // queryByTestId returns null when the element is missing.
    expect(
      screen.queryByTestId('dashboard-view-all-activities'),
    ).not.toBeInTheDocument();
  });
});
