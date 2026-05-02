/**
 * Tests for the Aktivitäten page (TF-337).
 *
 * Mirrors the test patterns used by Auswertungen.test.tsx: mock the
 * service module, mount through MemoryRouter + ThemeProvider, drive
 * via testing-library queries.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';

import Aktivitaeten from '../Aktivitaeten';
import { ActivityService, ApiError } from '../../services/activityService';
import { ActivityListResponse } from '../../types/activity';

// date-fns v3+ ships locale/* as ESM, which CRA's Babel transform can't
// parse out of the box. Mocking the locale module sidesteps the
// transform without touching jest config; the page only uses the
// imported objects as opaque tokens passed to formatDistanceToNow.
jest.mock('date-fns/locale', () => ({ de: {}, enUS: {}, fr: {}, it: {} }));
jest.mock('date-fns', () => ({
  formatDistanceToNow: () => 'vor 1 Stunde',
}));

jest.mock('../../services/activityService', () => {
  // We need a real ApiError class so tests can `throw new ApiError`.
  class ApiErrorImpl extends Error {
    kind: string;
    status: number;
    detail: unknown;
    issues: string[];
    constructor(p: {
      kind: string;
      status: number;
      message: string;
      detail?: unknown;
      issues?: string[];
    }) {
      super(p.message);
      this.name = 'ApiError';
      this.kind = p.kind;
      this.status = p.status;
      this.detail = p.detail;
      this.issues = p.issues ?? [];
    }
  }
  return {
    ApiError: ApiErrorImpl,
    ActivityService: { list: jest.fn() },
  };
});

const mockList = ActivityService.list as jest.MockedFunction<
  typeof ActivityService.list
>;

const theme = createTheme();

const renderPage = () =>
  render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <Aktivitaeten />
      </ThemeProvider>
    </MemoryRouter>,
  );

const sampleResponse = (
  overrides: Partial<ActivityListResponse> = {},
): ActivityListResponse => ({
  items: [
    {
      id: 'audit_1',
      type: 'document_uploaded',
      title: 'doc.pdf',
      timestamp: '2026-05-01T10:00:00Z',
      actor_user_id: null,
    },
    {
      id: 'audit_2',
      type: 'questions_generated',
      title: 'RAG-Topic',
      timestamp: '2026-05-01T09:00:00Z',
      actor_user_id: null,
    },
  ],
  total: 2,
  limit: 25,
  offset: 0,
  has_more: false,
  ...overrides,
});

describe('Aktivitäten page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default to "use last call's response" so early renders that
    // race the first await don't crash with .then on undefined.
    mockList.mockResolvedValue(sampleResponse());
  });

  test('renders list and shows item titles after the service resolves', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('aktivitaeten-list')).toBeInTheDocument();
    });
    expect(screen.getByText('doc.pdf')).toBeInTheDocument();
    expect(screen.getByText('RAG-Topic')).toBeInTheDocument();
  });

  test('default scope is own and types are not sent when all chips active', async () => {
    renderPage();
    await waitFor(() => expect(mockList).toHaveBeenCalled());
    const firstArg = mockList.mock.calls[0][0]!;
    expect(firstArg.scope).toBe('own');
    // All 7 chips active → component omits ``types`` so the backend
    // takes its implicit "all supported types" code path.
    expect(firstArg.types).toBeUndefined();
    expect(firstArg.limit).toBe(25);
    expect(firstArg.offset).toBe(0);
  });

  test('toggling scope to institution refetches with scope=institution', async () => {
    renderPage();
    await waitFor(() => expect(mockList).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId('aktivitaeten-scope-institution'));

    await waitFor(() => {
      const scopes = mockList.mock.calls.map((c) => c[0]?.scope);
      expect(scopes).toContain('institution');
    });
  });

  test('clicking a type chip deselects it and sends the remaining types', async () => {
    renderPage();
    await waitFor(() => expect(mockList).toHaveBeenCalled());

    // Toggle off "exam_deleted" → 6 remaining types in alphabetic
    // ACTIVITY_TYPES order, comma-joined.
    fireEvent.click(screen.getByTestId('aktivitaeten-chip-exam_deleted'));

    await waitFor(() => {
      const lastTypes =
        mockList.mock.calls[mockList.mock.calls.length - 1][0]?.types;
      expect(lastTypes).toEqual(
        expect.arrayContaining([
          'document_uploaded',
          'document_deleted',
          'questions_generated',
          'question_approved',
          'question_rejected',
          'exam_created',
        ]),
      );
    });
    const lastTypes =
      mockList.mock.calls[mockList.mock.calls.length - 1][0]?.types;
    expect(lastTypes).toHaveLength(6);
    expect(lastTypes).not.toContain('exam_deleted');
  });

  test('TablePagination next-page click triggers refetch with offset=25', async () => {
    // Mock so any subsequent call still gets data — TablePagination
    // re-renders and refires the effect a few times.
    mockList.mockImplementation(async (params) => ({
      items: sampleResponse().items,
      total: 60,
      limit: params?.limit ?? 25,
      offset: params?.offset ?? 0,
      has_more: (params?.offset ?? 0) + sampleResponse().items.length < 60,
    }));

    renderPage();
    // Wait for the list to actually render — the pagination control
    // is part of the list TableContainer, so without this the next
    // button won't exist yet.
    await screen.findByTestId('aktivitaeten-pagination');

    const nextBtn = screen.getByRole('button', { name: /next page/i });
    fireEvent.click(nextBtn);

    await waitFor(() => {
      const offsets = mockList.mock.calls.map((c) => c[0]?.offset);
      expect(offsets).toContain(25);
    });
  });

  test('empty result + all filters active shows fresh-empty state with shortcuts', async () => {
    // mockResolvedValue (not Once): React StrictMode + the
    // typesParam useMemo can re-fire the effect; sticking to the
    // fixed empty payload keeps the assertion deterministic.
    mockList.mockResolvedValue(sampleResponse({ items: [], total: 0 }));
    renderPage();

    expect(
      await screen.findByTestId('aktivitaeten-empty-fresh'),
    ).toBeInTheDocument();
  });

  test('empty result + filters active shows filtered-empty state with reset button', async () => {
    // Initial fetch returns data so we can interact with the chip.
    // Subsequent fetches return empty so the filter-toggle lands us
    // on the empty-filtered branch and the reset goes back to fresh.
    let callCount = 0;
    mockList.mockImplementation(async () => {
      callCount += 1;
      if (callCount === 1) return sampleResponse();
      return sampleResponse({ items: [], total: 0 });
    });

    renderPage();
    expect(await screen.findByText('doc.pdf')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('aktivitaeten-chip-exam_deleted'));

    expect(
      await screen.findByTestId('aktivitaeten-empty-filtered'),
    ).toBeInTheDocument();

    // Reset button restores all chips + scope and refires; assert via
    // the request shape (the visible state machine shifts from
    // empty-filtered to empty-fresh, but both renderings flicker
    // through loading first — checking the request is sturdier).
    fireEvent.click(screen.getByTestId('aktivitaeten-reset-filters'));

    await waitFor(() => {
      const lastArg = mockList.mock.calls[mockList.mock.calls.length - 1][0]!;
      expect(lastArg.types).toBeUndefined();
    });
    const lastArg = mockList.mock.calls[mockList.mock.calls.length - 1][0]!;
    expect(lastArg.scope).toBe('own');
    expect(lastArg.offset).toBe(0);
  });

  test('does not render stale result when filter changes mid-flight', async () => {
    // Regression guard for the AbortController + inFlightRef pattern.
    // Without it, a slow first request resolving AFTER a fast second
    // request would overwrite the fresh data with stale data.
    let resolveSlow: (value: ActivityListResponse) => void = () => {};
    const slowPromise = new Promise<ActivityListResponse>((resolve) => {
      resolveSlow = resolve;
    });

    let callCount = 0;
    mockList.mockImplementation(async (params) => {
      callCount += 1;
      if (callCount === 1) {
        // First call (initial mount) — slow, will resolve LAST with
        // stale "doc.pdf" data the user already navigated away from.
        return slowPromise;
      }
      // Second call (after chip toggle) — fast, returns empty/fresh.
      return sampleResponse({ items: [], total: 0 });
    });

    renderPage();

    // Wait for the first request to be in flight, then toggle a chip
    // to trigger the second.
    await waitFor(() => expect(mockList).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByTestId('aktivitaeten-chip-exam_deleted'));
    await waitFor(() => expect(mockList).toHaveBeenCalledTimes(2));

    // Now resolve the slow first call — its result should be dropped
    // because the controller was aborted by the second-call effect.
    resolveSlow(sampleResponse());

    // Empty-filtered state appears (from call #2), and the stale
    // "doc.pdf" from call #1 must NOT render.
    expect(
      await screen.findByTestId('aktivitaeten-empty-filtered'),
    ).toBeInTheDocument();
    expect(screen.queryByText('doc.pdf')).not.toBeInTheDocument();
  });

  test('error from the service surfaces an alert with reload button', async () => {
    // First call rejects, all later calls resolve to data so the
    // reload button can verify the recovery path. Using
    // mockImplementation lets us drive both behaviours from one mock
    // without ordering pitfalls between StrictMode re-runs.
    let calls = 0;
    mockList.mockImplementation(async () => {
      calls += 1;
      if (calls === 1) {
        throw new ApiError({
          kind: 'server',
          status: 502,
          message: 'Bad Gateway',
        });
      }
      return sampleResponse();
    });

    renderPage();

    expect(await screen.findByTestId('aktivitaeten-error')).toBeInTheDocument();
    expect(screen.getByText('Bad Gateway')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('aktivitaeten-reload'));
    expect(await screen.findByText('doc.pdf')).toBeInTheDocument();
  });
});
