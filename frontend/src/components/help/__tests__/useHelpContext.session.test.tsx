import React from 'react';
import { renderHook, waitFor, act, render } from '@testing-library/react';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import { useHelpContext } from '../useHelpContext';
import { helpService, ContextHint } from '../../../services/HelpService';

jest.mock('../../../services/HelpService', () => ({
  helpService: {
    getStatus: jest.fn(),
    getOnboardingStatus: jest.fn(),
    getContextHint: jest.fn(),
  },
}));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ accessToken: 'token', hasRole: () => false }),
}));

const mocked = helpService as jest.Mocked<typeof helpService>;

/** The four teacher hints, in the order the app's workflow visits them. */
const HINTS: Record<string, ContextHint> = {
  '/documents': { i18n_key: 'help.hints.documents', hint_id: 7 },
  '/questions/generate': { i18n_key: 'help.hints.questionsGenerate', hint_id: 8 },
  '/questions/review': { i18n_key: 'help.hints.questionsReview', hint_id: 5 },
  '/exams/compose': { i18n_key: 'help.hints.examsCompose', hint_id: 6 },
};

const NO_HINT: ContextHint = { i18n_key: null, hint_id: null };

const wrapper = (route: string) =>
  ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
  );

beforeEach(() => {
  sessionStorage.clear();
  jest.clearAllMocks();
  mocked.getStatus.mockResolvedValue({ modes: { onboarding: true, context: true, chat: false } });
  mocked.getOnboardingStatus.mockResolvedValue({
    role: 'teacher',
    current_step: 8,
    completed_steps: [0, 1, 2, 3, 4, 5, 6, 7],
    skipped_steps: [],
    completed: true,
  } as any);
  mocked.getContextHint.mockImplementation(
    async (_token: string, route: string) => HINTS[route] ?? NO_HINT
  );
});

/**
 * The regression this change is about: TF-308 capped a session at three hints
 * as flood protection, written when no role could reach more than two. Once
 * the two dead route patterns were fixed a teacher had four, and the fourth —
 * `/exams/compose`, always last in the workflow — became unreachable.
 */
test('shows every hint in the workflow, however many came before', async () => {
  for (const route of Object.keys(HINTS)) {
    const { result, unmount } = renderHook(() => useHelpContext(), { wrapper: wrapper(route) });
    await waitFor(() => expect(result.current.contextHint?.hint_id).toBe(HINTS[route].hint_id));
    act(() => result.current.acknowledgeHint(HINTS[route].hint_id!));
    unmount();
  }
});

test('a hint stays until the user acknowledges it, across navigation', async () => {
  const { result, unmount } = renderHook(() => useHelpContext(), { wrapper: wrapper('/documents') });
  await waitFor(() => expect(result.current.contextHint?.hint_id).toBe(7));
  unmount(); // navigated away without touching either button

  const { result: onReturn } = renderHook(() => useHelpContext(), { wrapper: wrapper('/documents') });
  await waitFor(() => expect(onReturn.current.hasContextHint).toBe(true));
  expect(onReturn.current.contextHint?.hint_id).toBe(7);
});

test('"Verstanden" hides the hint immediately and on return', async () => {
  const { result, unmount } = renderHook(() => useHelpContext(), { wrapper: wrapper('/documents') });
  await waitFor(() => expect(result.current.contextHint?.hint_id).toBe(7));

  act(() => result.current.acknowledgeHint(7));
  expect(result.current.hasContextHint).toBe(false);
  unmount();

  const { result: onReturn } = renderHook(() => useHelpContext(), { wrapper: wrapper('/documents') });
  await waitFor(() => expect(onReturn.current.loading).toBe(false));
  expect(onReturn.current.hasContextHint).toBe(false);
});

/**
 * The single-slot `dismissedHintId` on HelpWidget held one id, so
 * acknowledging a second hint resurrected the first.
 */
test('acknowledging one hint does not resurrect another', async () => {
  const { result: onDocuments, unmount: leaveDocuments } = renderHook(() => useHelpContext(), {
    wrapper: wrapper('/documents'),
  });
  await waitFor(() => expect(onDocuments.current.contextHint?.hint_id).toBe(7));
  act(() => onDocuments.current.acknowledgeHint(7));
  leaveDocuments();

  const { result: onGenerate, unmount: leaveGenerate } = renderHook(() => useHelpContext(), {
    wrapper: wrapper('/questions/generate'),
  });
  await waitFor(() => expect(onGenerate.current.contextHint?.hint_id).toBe(8));
  act(() => onGenerate.current.acknowledgeHint(8));
  leaveGenerate();

  const { result: backOnFirst } = renderHook(() => useHelpContext(), {
    wrapper: wrapper('/documents'),
  });
  await waitFor(() => expect(backOnFirst.current.loading).toBe(false));
  expect(backOnFirst.current.hasContextHint).toBe(false);
});

test('routes without a hint neither record nor block anything', async () => {
  const { result } = renderHook(() => useHelpContext(), { wrapper: wrapper('/dashboard') });
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.hasContextHint).toBe(false);
  expect(sessionStorage.getItem('ec_help_hints_acknowledged')).toBeNull();
});

/**
 * `hintByRouteRef` exists specifically so every navigation doesn't re-hit
 * `/help/context` and trip the IP rate limiter — but the tests above all
 * unmount and remount per route, which resets that ref to a fresh empty Map
 * every time. None of them can actually distinguish a working cache from no
 * cache at all. This one stays mounted across a same-mount route revisit,
 * the case the cache exists for.
 */
test('a same-mount route revisit is served from cache, not refetched', async () => {
  const results: ReturnType<typeof useHelpContext>[] = [];
  let navigate: (route: string) => void = () => {};

  function Harness() {
    const nav = useNavigate();
    navigate = nav;
    const result = useHelpContext();
    results.push(result);
    return null;
  }

  render(
    <MemoryRouter initialEntries={['/documents']}>
      <Harness />
    </MemoryRouter>
  );

  await waitFor(() => expect(results[results.length - 1].contextHint?.hint_id).toBe(7));
  expect(mocked.getContextHint).toHaveBeenCalledTimes(1);

  act(() => navigate('/questions/generate'));
  await waitFor(() =>
    expect(results[results.length - 1].contextHint?.hint_id).toBe(8)
  );
  expect(mocked.getContextHint).toHaveBeenCalledTimes(2);

  // Same mount, back to a route already fetched once — the cache should
  // serve it without a third network call.
  act(() => navigate('/documents'));
  await waitFor(() =>
    expect(results[results.length - 1].contextHint?.hint_id).toBe(7)
  );
  expect(mocked.getContextHint).toHaveBeenCalledTimes(2);
});
