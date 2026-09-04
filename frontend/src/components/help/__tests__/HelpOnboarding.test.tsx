import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { SIDEBAR_REVEAL_NAV_EVENT, SidebarRevealNavDetail } from '../../layout/sidebarNavReveal';

// Capture driver.js calls so tests can trigger callbacks
let capturedHighlightConfig: any = null;
let capturedDriverConfig: any = null;
const mockDestroy = jest.fn();
const mockRefresh = jest.fn();
const mockHighlight = jest.fn((config: any) => { capturedHighlightConfig = config; });
const mockDriverInstance = { highlight: mockHighlight, destroy: mockDestroy, refresh: mockRefresh };
const mockDriverFactory = jest.fn((config: any) => {
  capturedDriverConfig = config;
  return mockDriverInstance;
});

jest.mock('driver.js', () => ({
  driver: (config: any) => mockDriverFactory(config),
}));
jest.mock('driver.js/dist/driver.css', () => {});

import HelpOnboarding, { OnboardingStep } from '../HelpOnboarding';

const mockStatus = { id: 1, role: 'teacher', current_step: 1, completed_steps: [0], completed: false };

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

const renderOnboarding = (overrides: Partial<React.ComponentProps<typeof HelpOnboarding>> = {}) => {
  const props = {
    status: mockStatus,
    steps: [doneStep, navStep, doneStep],
    active: false,
    onCompleteStep: jest.fn().mockResolvedValue(undefined),
    onSkipStep: jest.fn().mockResolvedValue(undefined),
    onTourComplete: jest.fn(),
    onTourCancel: jest.fn(),
    ...overrides,
  };
  return { ...render(<MemoryRouter><HelpOnboarding {...props} /></MemoryRouter>), props };
};

let navDocumentsEl: HTMLElement;

beforeEach(() => {
  capturedHighlightConfig = null;
  capturedDriverConfig = null;
  mockDestroy.mockClear();
  mockHighlight.mockClear();
  mockRefresh.mockClear();
  // Inject nav element so highlightNavStep doesn't skip (new upfront DOM check)
  navDocumentsEl = document.createElement('a');
  navDocumentsEl.setAttribute('data-testid', 'nav-documents');
  document.body.appendChild(navDocumentsEl);
});

afterEach(() => {
  navDocumentsEl?.remove();
});

describe('HelpOnboarding — Texte aus translation.json', () => {
  /**
   * The popover text used to come from `title_de`/`title_en` fields on the step
   * itself. Nothing asserted on it, so when the texts moved into
   * translation.json a dead `i18n_key` would have rendered the raw key and
   * every test would still have passed (TF-670).
   */
  it('zeigt Titel und Text des Schritts, nicht den Schlüssel', () => {
    renderOnboarding({
      active: true,
      status: { ...mockStatus, current_step: 1 },
    });

    const popover = screen.getByTestId('onboarding-popover');
    // navStep points at help.tour.teacher.core.2 — the upload step.
    expect(popover).toHaveTextContent('Dokument hochladen');
    expect(popover.textContent).not.toContain('help.tour.');
  });

  it('beschriftet die Knöpfe aus translation.json', () => {
    renderOnboarding({
      active: true,
      status: { ...mockStatus, current_step: 1 },
    });

    expect(screen.getByTestId('onboarding-popover-close')).toHaveTextContent('Tour beenden');
  });
});

describe('HelpOnboarding — confirmation dialog', () => {
  it('calls onTourCancel (not onTourComplete) when user clicks "Ja, beenden"', async () => {
    const { props } = renderOnboarding({
      active: true,
      status: { ...mockStatus, current_step: 1 },
    });

    expect(mockHighlight).toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('onboarding-popover-close'));

    expect(screen.getByText(/Tour beenden\?/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Ja, beenden/i }));

    expect(props.onTourCancel).toHaveBeenCalledTimes(1);
    expect(props.onTourComplete).not.toHaveBeenCalled();
  });

  it('hides dialog when user clicks "Abbrechen"', async () => {
    renderOnboarding({
      active: true,
      status: { ...mockStatus, current_step: 1 },
    });

    fireEvent.click(screen.getByTestId('onboarding-popover-close'));

    expect(screen.getByText(/Tour beenden\?/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Abbrechen/i }));

    expect(screen.queryByText(/Tour beenden\?/i)).not.toBeInTheDocument();
  });
});

describe('HelpOnboarding — nav_selector not in DOM', () => {
  it('calls onSkipStep to skip when nav_selector element stays absent', async () => {
    // Remove the nav element injected by beforeEach so this test has it absent.
    // Nothing answers the reveal request (no sidebar), so the step is skipped
    // once the reveal budget is exhausted.
    navDocumentsEl?.remove();

    const onSkipStep = jest.fn().mockResolvedValue(undefined);
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    // Fake timers (review fix): the real-timer version of this test only had
    // ~250ms margin over the ~550ms worst case (500ms budget + one 50ms poll
    // tick), which is thin under a loaded/parallel CI runner. Advancing fake
    // timers makes the wait deterministic and exact instead of "hopefully
    // enough margin".
    jest.useFakeTimers();

    try {
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 1 },
        steps: [doneStep, navStep, doneStep],
        onSkipStep,
      });

      // This Jest install exposes only legacy-style fake timers (no
      // jest.advanceTimersByTimeAsync) -- advance synchronously inside
      // act(async () => ...) so the microtask queue (onSkipStep's .then)
      // still gets a chance to flush between timer callbacks.
      await act(async () => {
        jest.advanceTimersByTime(600);
      });

      expect(onSkipStep).toHaveBeenCalledWith(1);
      // TF-604: skipping must no longer be silent.
      expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('Step 1 skipped'));
    } finally {
      warnSpy.mockRestore();
      jest.useRealTimers();
    }
  });
});

describe('HelpOnboarding — route not in the user\'s navigation (RBAC)', () => {
  /**
   * A Dozent has one page under "Auswertungen" where an admin has three. The
   * tour used to discover that by asking the sidebar to reveal a link that does
   * not exist and waiting out the 500ms budget — per step. Reported from the
   * field as "I click Weiter, the tour vanishes, and 1–2s later the widget
   * tells me it's done".
   */
  it('skips immediately, without dispatching a reveal or waiting out the budget', () => {
    const dispatchSpy = jest.spyOn(window, 'dispatchEvent');
    const onSkipStep = jest.fn().mockResolvedValue(undefined);

    try {
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 1 },
        steps: [doneStep, navStep, doneStep],
        onSkipStep,
        isRouteAccessible: () => false,
      });

      // No timer advance: the point is that no waiting happens at all.
      expect(onSkipStep).toHaveBeenCalledWith(1);
      expect(mockHighlight).not.toHaveBeenCalled();

      const revealDispatched = dispatchSpy.mock.calls.some(
        ([event]) => (event as CustomEvent).type === SIDEBAR_REVEAL_NAV_EVENT,
      );
      expect(revealDispatched).toBe(false);
    } finally {
      dispatchSpy.mockRestore();
    }
  });

  /**
   * RBAC filtering is expected, not an anomaly. Warning about it (and paging
   * Sentry) is what trained everyone to ignore the signal that TF-604 added
   * for the genuinely broken case.
   */
  it('reports an RBAC skip at debug level, not as a warning', () => {
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const debugSpy = jest.spyOn(console, 'debug').mockImplementation(() => {});

    try {
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 1 },
        steps: [doneStep, navStep, doneStep],
        onSkipStep: jest.fn().mockResolvedValue(undefined),
        isRouteAccessible: () => false,
      });

      expect(debugSpy).toHaveBeenCalledWith(
        expect.stringContaining('Step 1 not applicable'),
      );
      expect(warnSpy).not.toHaveBeenCalled();
    } finally {
      warnSpy.mockRestore();
      debugSpy.mockRestore();
    }
  });

  it('still warns when a reachable step\'s element is genuinely missing', async () => {
    navDocumentsEl?.remove();
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.useFakeTimers();

    try {
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 1 },
        steps: [doneStep, navStep, doneStep],
        onSkipStep: jest.fn().mockResolvedValue(undefined),
        isRouteAccessible: () => true,
      });

      await act(async () => {
        jest.advanceTimersByTime(600);
      });

      expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('Step 1 skipped'));
    } finally {
      warnSpy.mockRestore();
      jest.useRealTimers();
    }
  });

  /**
   * The button on the last *visible* step has to say "Fertig", not "Weiter" —
   * otherwise the tour promises pages that will never come, which is what the
   * report was actually about.
   */
  it('labels the last reachable step "Fertig", ignoring unreachable later steps', () => {
    // `route: null` keeps this on the spotlight path — MemoryRouter starts at
    // '/', so a routed step would go down the nav branch instead.
    const current: OnboardingStep = {
      ...navStep,
      step: 1,
      route: null,
      highlight_selector: "[data-testid='auswertungen-page']",
      nav_selector: null,
    };
    const later: OnboardingStep = {
      ...navStep,
      step: 2,
      route: '/auswertungen/klassen',
      highlight_selector: "[data-testid='klassen-page']",
      nav_selector: null,
    };

    const anchor = document.createElement('div');
    anchor.setAttribute('data-testid', 'auswertungen-page');
    document.body.appendChild(anchor);
    jest.useFakeTimers();

    try {
      const { unmount } = renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 0 },
        steps: [current, later],
        isRouteAccessible: () => false,
      });
      act(() => { jest.advanceTimersByTime(500); });
      expect(screen.getByTestId('onboarding-popover-next')).toHaveTextContent(/Fertig/);
      unmount();

      // Contrast: the same step list with the later step reachable must still
      // say "Weiter" — otherwise this test would pass on a hardcoded label.
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 0 },
        steps: [current, later],
        isRouteAccessible: () => true,
      });
      act(() => { jest.advanceTimersByTime(500); });
      expect(screen.getByTestId('onboarding-popover-next')).toHaveTextContent(/Weiter/);
    } finally {
      jest.useRealTimers();
      anchor.remove();
    }
  });
});

describe('HelpOnboarding — nav_selector already in DOM (fast path)', () => {
  it('highlights synchronously without dispatching a reveal request', () => {
    // navDocumentsEl is already in the DOM from beforeEach -- the opposite
    // fixture from the collapsed-sidebar tests below. This locks in the PR's
    // own stated goal ("a link that's already rendered is still highlighted
    // synchronously — no additional flicker") as a dedicated assertion
    // instead of relying on it as an incidental side effect of the unrelated
    // confirmation-dialog tests above (review fix).
    const dispatchSpy = jest.spyOn(window, 'dispatchEvent');
    const onSkipStep = jest.fn().mockResolvedValue(undefined);

    try {
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 1 },
        steps: [doneStep, navStep, doneStep],
        onSkipStep,
      });

      // No wait on purpose: if the fast path regressed to always going
      // through waitForNavElement's setTimeout chain, this assertion fails
      // immediately rather than needing a timing-dependent wait to notice.
      expect(mockHighlight).toHaveBeenCalled();
      expect(capturedHighlightConfig?.element).toBe("[data-testid='nav-documents']");
      expect(onSkipStep).not.toHaveBeenCalled();

      const revealDispatched = dispatchSpy.mock.calls.some(
        ([event]) => (event as CustomEvent).type === SIDEBAR_REVEAL_NAV_EVENT,
      );
      expect(revealDispatched).toBe(false);
    } finally {
      dispatchSpy.mockRestore();
    }
  });
});

describe('HelpOnboarding — nav link below the sidebar fold (TF-625)', () => {
  /**
   * The sidebar nav is its own `overflow-y-auto` container, so entries far
   * down the list sit outside the visible area. driver.js will not rescue
   * that: it skips scrolling whenever the element is inside the window
   * viewport, and the overlay blocks the user from scrolling the sidebar by
   * hand — the tour dead-ends on that step. Found manually on
   * "Prompt-Bibliothek".
   */
  it('scrolls the nav link into view before driver.js measures it', () => {
    const scrollSpy = jest.fn();
    // jsdom implements no scrollIntoView, so there is nothing to spy on —
    // define it, which doubles as the guard the component has to respect.
    (navDocumentsEl as HTMLElement).scrollIntoView = scrollSpy;

    renderOnboarding({
      active: true,
      status: { ...mockStatus, current_step: 1 },
      steps: [doneStep, navStep, doneStep],
    });

    expect(scrollSpy).toHaveBeenCalledWith(
      expect.objectContaining({ block: 'center' }),
    );
    // Order matters: scrolling after the highlight would leave driver.js's
    // cutout at the pre-scroll position.
    expect(scrollSpy.mock.invocationCallOrder[0]).toBeLessThan(
      mockHighlight.mock.invocationCallOrder[0],
    );
  });

  it('does not crash when scrollIntoView is unavailable', () => {
    // Guard for jsdom and any host lacking the API — the element in
    // beforeEach has no scrollIntoView at all.
    expect(() =>
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 1 },
        steps: [doneStep, navStep, doneStep],
      }),
    ).not.toThrow();
    expect(mockHighlight).toHaveBeenCalled();
  });
});

describe('HelpOnboarding — collapsed sidebar group (TF-604)', () => {
  /**
   * Stand-in for the Sidebar: renders the nav link only once a reveal request
   * for its route arrives — mirroring a collapsed group whose items are not in
   * the DOM until it is expanded.
   */
  const mountCollapsedSidebar = (route: string, testId: string) => {
    let el: HTMLElement | null = null;
    const listener = (event: Event) => {
      const detail = (event as CustomEvent<SidebarRevealNavDetail>).detail;
      if (detail?.path !== route || el) return;
      el = document.createElement('a');
      el.setAttribute('data-testid', testId);
      document.body.appendChild(el);
    };
    window.addEventListener(SIDEBAR_REVEAL_NAV_EVENT, listener);
    return () => {
      window.removeEventListener(SIDEBAR_REVEAL_NAV_EVENT, listener);
      el?.remove();
    };
  };

  it('reveals the nav link and highlights it instead of skipping the step', async () => {
    navDocumentsEl?.remove();
    const cleanup = mountCollapsedSidebar('/documents', 'nav-documents');
    const onSkipStep = jest.fn().mockResolvedValue(undefined);

    try {
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 1 },
        steps: [doneStep, navStep, doneStep],
        onSkipStep,
      });

      await act(async () => {
        await new Promise(r => setTimeout(r, 200));
      });

      expect(onSkipStep).not.toHaveBeenCalled();
      expect(capturedHighlightConfig?.element).toBe("[data-testid='nav-documents']");
    } finally {
      cleanup();
    }
  });

  it('also reveals links for steps without an explicit nav_selector', async () => {
    // Selector derived from the route — same collapsed-group problem.
    const derivedStep: OnboardingStep = { ...navStep, nav_selector: null };
    navDocumentsEl?.remove();
    const cleanup = mountCollapsedSidebar('/documents', 'nav-documents');
    const onSkipStep = jest.fn().mockResolvedValue(undefined);

    try {
      renderOnboarding({
        active: true,
        status: { ...mockStatus, current_step: 1 },
        steps: [doneStep, derivedStep, doneStep],
        onSkipStep,
      });

      await act(async () => {
        await new Promise(r => setTimeout(r, 200));
      });

      expect(onSkipStep).not.toHaveBeenCalled();
      expect(capturedHighlightConfig?.element).toBe("[data-testid='nav-documents']");
    } finally {
      cleanup();
    }
  });
});

const tabStep: OnboardingStep = {
  step: 7,
  i18n_key: 'help.tour.admin.tracks.admin-benutzer.steps.1',
  route: '/admin',
  highlight_selector: "[data-testid='admin-tab-content-institutions']",
  nav_selector: null,
  tab_selector: "[data-testid='admin-tab-btn-institutions']",
};

describe('HelpOnboarding — TAB_NAVIGATING mode', () => {
  it('skips tab step when tab_selector element is not in DOM', async () => {
    const onSkipStep = jest.fn().mockResolvedValue(undefined);

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <HelpOnboarding
          status={{ ...mockStatus, current_step: 7 }}
          steps={[...Array(7).fill(doneStep), tabStep, doneStep]}
          active={true}
          onCompleteStep={jest.fn().mockResolvedValue(undefined)}
          onSkipStep={onSkipStep}
          onTourComplete={jest.fn()}
          onTourCancel={jest.fn()}
        />
      </MemoryRouter>
    );

    await act(async () => {
      await new Promise(r => setTimeout(r, 600));
    });

    expect(onSkipStep).toHaveBeenCalledWith(7);
  });

  it('highlights tab_selector element when on correct route and tab button exists', async () => {
    const tabBtn = document.createElement('button');
    tabBtn.setAttribute('data-testid', 'admin-tab-btn-institutions');
    document.body.appendChild(tabBtn);

    try {
      render(
        <MemoryRouter initialEntries={['/admin']}>
          <HelpOnboarding
            status={{ ...mockStatus, current_step: 7 }}
            steps={[...Array(7).fill(doneStep), tabStep, doneStep]}
            active={true}
            onCompleteStep={jest.fn().mockResolvedValue(undefined)}
            onSkipStep={jest.fn().mockResolvedValue(undefined)}
            onTourComplete={jest.fn()}
            onTourCancel={jest.fn()}
          />
        </MemoryRouter>
      );

      await act(async () => {
        await new Promise(r => setTimeout(r, 600));
      });

      expect(mockHighlight).toHaveBeenCalled();
      expect(capturedHighlightConfig?.element).toBe("[data-testid='admin-tab-btn-institutions']");
    } finally {
      document.body.removeChild(tabBtn);
    }
  });
});
