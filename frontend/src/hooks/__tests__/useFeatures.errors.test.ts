import { renderHook, waitFor } from '@testing-library/react';
import { useFeatures } from '../useFeatures';

/**
 * Wiring test for useFeatures' translateError() call — one of the three
 * files (alongside GenerationTasksBar.tsx and ChatInterface.tsx) that the
 * RAGExamCreator.errorChain.test.tsx header comment says produced real bugs
 * during TF-671 development precisely because each half looked testable in
 * isolation. This is the missing "other half" for useFeatures.ts.
 */

let mockUser: { id: number } | null = { id: 1 };
let mockAccessToken: string | null = 'token-123';
let mockIsAuthenticated = true;

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    accessToken: mockAccessToken,
    isAuthenticated: mockIsAuthenticated,
  }),
}));

const originalFetch = global.fetch;

beforeEach(() => {
  mockUser = { id: 1 };
  mockAccessToken = 'token-123';
  mockIsAuthenticated = true;
  localStorage.clear();
});

afterEach(() => {
  global.fetch = originalFetch;
  jest.restoreAllMocks();
});

describe('useFeatures — Fehler erreichen die UI übersetzt, nie roh', () => {
  it('zeigt die übersetzte Standardmeldung bei einem HTTP-Fehler', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      json: async () => ({}),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useFeatures());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe('Die verfügbaren Funktionen konnten nicht geladen werden.');
    // The raw HTTP status text must never leak into the UI-facing error.
    expect(result.current.error).not.toContain('Service Unavailable');
    expect(result.current.error).not.toContain('503');
  });

  it('zeigt die übersetzte Standardmeldung bei einem Netzwerkfehler', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('Failed to fetch')) as unknown as typeof fetch;

    const { result } = renderHook(() => useFeatures());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe('Die verfügbaren Funktionen konnten nicht geladen werden.');
    expect(result.current.error).not.toContain('Failed to fetch');
  });

  it('ruft fetch bei stabiler t-Identität nur einmal auf (Regressionsschutz gegen Render-Schleife)', async () => {
    // useFeatures' fetchFeatures useCallback lists `t` as a dependency; a
    // mock that hands out a fresh `t` closure per render would make this
    // effect refire every render and either loop or double-fetch — see
    // setupTests.ts's react-i18next mock for the fix this guards.
    const fetchMock = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({}),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const { result, rerender } = renderHook(() => useFeatures());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    rerender();
    rerender();

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
