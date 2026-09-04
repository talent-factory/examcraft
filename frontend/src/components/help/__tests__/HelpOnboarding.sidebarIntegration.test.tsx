/**
 * HelpOnboarding + Sidebar integration (TF-604 review fix).
 *
 * The unit tests in HelpOnboarding.test.tsx and Sidebar.test.tsx each stand
 * in for the other side: HelpOnboarding's tests use a hand-rolled
 * `window.addEventListener` stand-in for the Sidebar, and Sidebar's tests
 * dispatch the reveal event directly rather than going through
 * HelpOnboarding's actual polling code. Both prove their own component's
 * contract in isolation, but neither exercises the real event dispatch →
 * Sidebar's `useEffect` listener → `setExpandedGroups` → re-render → DOM
 * commit → HelpOnboarding's poll round-trip this PR is actually about.
 *
 * This file renders the real `Sidebar` and `HelpOnboarding` together to
 * prove that round-trip actually works end-to-end, not just each side's
 * contract against a substitute.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../../../contexts/AuthContext';
import { Sidebar } from '../../layout/Sidebar';
import HelpOnboarding, { OnboardingStep } from '../HelpOnboarding';

// Mock apiClient (uses axios ESM which Jest cannot transform) — same mock as
// Sidebar.test.tsx, needed transitively via AuthProvider/Sidebar.
jest.mock('../../../api/apiClient', () => ({
  setTokenRefreshCallback: jest.fn(),
  setLogoutCallback: jest.fn(),
  setAdoptStoredTokensCallback: jest.fn(),
  setupFetchInterceptor: jest.fn(),
  apiClient: { interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } },
}));

// Mock useRoleBasedNavigation so the collapsed-group fixture is deterministic
// (same pattern as Sidebar.test.tsx) rather than depending on real RBAC data.
const mockUseRoleBasedNavigation = jest.fn();
jest.mock('../../../hooks/useRoleBasedNavigation', () => ({
  useRoleBasedNavigation: () => mockUseRoleBasedNavigation(),
}));

// Capture driver.js calls so the test can assert what HelpOnboarding actually
// highlighted, same mock as HelpOnboarding.test.tsx.
let capturedHighlightConfig: any = null;
const mockHighlight = jest.fn((config: any) => { capturedHighlightConfig = config; });
const mockDriverInstance = { highlight: mockHighlight, destroy: jest.fn() };
jest.mock('driver.js', () => ({ driver: jest.fn(() => mockDriverInstance) }));
jest.mock('driver.js/dist/driver.css', () => {});

const navigationGroups = [
  { id: 'overview', label: 'Überblick', items: [{ label: 'Dashboard', path: '/dashboard', icon: '📊' }] },
  // Owns the tour's nav step. NOT the active route's group, so it starts
  // collapsed -- the actual TF-604 regression scenario, not a synthetic one.
  { id: 'documents-group', label: 'Dokumente', items: [{ label: 'Dokumente', path: '/documents', icon: '📄' }] },
];

beforeEach(() => {
  window.localStorage.clear();
  capturedHighlightConfig = null;
  mockHighlight.mockClear();
  mockUseRoleBasedNavigation.mockReturnValue({
    navigationGroups,
    navigationItems: navigationGroups.flatMap((g) => g.items),
  });
});

const navStep: OnboardingStep = {
  step: 1,
  i18n_key: 'help.tour.teacher.core.2',
  route: '/documents',
  highlight_selector: "[data-testid='upload-area']",
  nav_selector: "[data-testid='nav-documents']",
  tab_selector: null,
};

const doneStep: OnboardingStep = {
  step: 2,
  i18n_key: 'help.tour.teacher.core.7',
  route: null,
  highlight_selector: null,
  nav_selector: null,
  tab_selector: null,
};

describe('HelpOnboarding + Sidebar integration (TF-604)', () => {
  it('fixture sanity check: the documents group is genuinely collapsed by default', () => {
    // Guards the main test below against silently degrading to a no-op --
    // without this, a fixture change that made every group open by default
    // would make the reveal assertion pass for the wrong reason.
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Sidebar isOpen />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.queryByTestId('nav-documents')).not.toBeInTheDocument();
  });

  it('reveals a nav link owned by a genuinely collapsed group through the real event round-trip', async () => {
    const onSkipStep = jest.fn().mockResolvedValue(undefined);
    const onCompleteStep = jest.fn().mockResolvedValue(undefined);

    // active=true from the first render deliberately exercises the tightest
    // timing: Sidebar's listener and HelpOnboarding's dispatch both attach
    // within the same initial effect flush (React commits effects in tree
    // order, Sidebar before HelpOnboarding here) -- proving the real,
    // unmocked round-trip resolves correctly even in that same-tick case,
    // not just when there's a real async gap between the two mounts.
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Sidebar isOpen />
          <HelpOnboarding
            active
            status={{ id: 1, role: 'teacher', current_step: 1, completed_steps: [0], completed: false }}
            steps={[doneStep, navStep, doneStep]}
            onCompleteStep={onCompleteStep}
            onSkipStep={onSkipStep}
            onTourComplete={jest.fn()}
            onTourCancel={jest.fn()}
          />
        </AuthProvider>
      </MemoryRouter>,
    );

    // Real timers, real React state update/re-render/DOM commit -- this is
    // the actual round-trip, not a rigged stand-in on either side. Waiting on
    // mockHighlight (not just the DOM element) is deliberate: the element can
    // appear in the DOM before HelpOnboarding's own poll notices (Sidebar's
    // state commit and HelpOnboarding's next scheduled poll tick are
    // independent timers), so asserting on the DOM alone would race
    // showNavHighlight actually having run. Generous wait budget (well above
    // NAV_REVEAL_TIMEOUT_MS) so this doesn't race waitForNavElement's own
    // timeout even under CI load.
    await waitFor(() => expect(mockHighlight).toHaveBeenCalled(), { timeout: 1000 });

    expect(onSkipStep).not.toHaveBeenCalled();
    expect(screen.getByTestId('nav-documents')).toBeInTheDocument();
    expect(capturedHighlightConfig?.element).toBe("[data-testid='nav-documents']");
  });

  it('survives StrictMode double-mounting (TF-625)', async () => {
    /**
     * The app renders under `React.StrictMode` (index.tsx), where React 18
     * runs effect → cleanup → effect in development. The cleanup latches
     * `isUnmountedRef`; until TF-625 nothing reset it on the second run, so
     * every waitForNavElement poll bailed on its first tick and left its
     * promise pending by design. Symptom in the browser: the group expands,
     * then nothing — no highlight, and the help widget stays unopenable
     * because `tourActive` never clears.
     *
     * This has to run against the real Sidebar. A hand-rolled stand-in that
     * inserts the link synchronously on the reveal event hides the bug: by
     * the second effect run the link is already in the DOM and
     * highlightNavStep takes its fast path, which never polls. The real
     * Sidebar reveals through a React state update, so the second run still
     * finds nothing and has to rely on the poll — the path that was broken.
     */
    const onSkipStep = jest.fn().mockResolvedValue(undefined);

    render(
      <React.StrictMode>
        <MemoryRouter initialEntries={['/dashboard']}>
          <AuthProvider>
            <Sidebar isOpen />
            <HelpOnboarding
              active
              status={{ id: 1, role: 'teacher', current_step: 1, completed_steps: [0], completed: false }}
              steps={[doneStep, navStep, doneStep]}
              onCompleteStep={jest.fn().mockResolvedValue(undefined)}
              onSkipStep={onSkipStep}
              onTourComplete={jest.fn()}
              onTourCancel={jest.fn()}
            />
          </AuthProvider>
        </MemoryRouter>
      </React.StrictMode>,
    );

    await waitFor(() => expect(mockHighlight).toHaveBeenCalled(), { timeout: 1000 });

    expect(onSkipStep).not.toHaveBeenCalled();
    expect(capturedHighlightConfig?.element).toBe("[data-testid='nav-documents']");
  });
});
