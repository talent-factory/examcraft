/**
 * Deep-dive tracks in the help widget (TF-625).
 *
 * Covers the three properties the ticket requires that the backend test
 * cannot see:
 *   1. Deep dives are startable independently of the core tour.
 *   2. A deep dive writes into its own progress space and leaves the core
 *      tour alone (`updateTrackStep` instead of `completeStep`).
 *   3. A deep dive whose routes the user cannot see via RBAC is not offered
 *      — otherwise it would run entirely down the skip path (acceptance
 *      criterion analogous to TF-604).
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { BrowserRouter } from 'react-router-dom';

const mockUpdateTrackStep = jest.fn().mockResolvedValue(undefined);
const mockCompleteStep = jest.fn().mockResolvedValue(undefined);

// Only `/auswertungen` is reachable for this user — the "einstellungen" track
// therefore has no accessible route at all.
const mockAccessiblePaths = new Set(['/auswertungen']);

// Deliberately fresh objects/functions on every call — exactly how the real
// hook behaves. A widget that uses that identity as a useEffect dependency
// runs into a render loop.
jest.mock('../../../hooks/useRoleBasedNavigation', () => ({
  useRoleBasedNavigation: () => ({
    navigationGroups: [],
    navigationItems: [...mockAccessiblePaths].map((path) => ({
      label: path,
      path,
    })),
    hasAccess: (path: string) => mockAccessiblePaths.has(path),
  }),
}));

jest.mock('../useHelpContext', () => ({
  useHelpContext: jest.fn(),
}));

// The chat pane's contents are irrelevant here — only whether it is mounted.
jest.mock('../HelpChat', () => () => <div data-testid="help-chat-stub" />);

// driver.js would otherwise build real overlays in jsdom.
const mockHighlight = jest.fn();
jest.mock('driver.js', () => ({
  driver: jest.fn(() => ({ highlight: mockHighlight, destroy: jest.fn() })),
}));
jest.mock('driver.js/dist/driver.css', () => ({}));

import HelpWidget from '../HelpWidget';

// i18n_key values point at real entries in de/translation.json — the test's
// i18n mock resolves against that file, so a broken key shows up as the key
// string instead of quietly rendering nothing.
const STEPS_FIXTURE = {
  teacher: {
    core: [
      {
        step: 0,
        i18n_key: 'help.tour.teacher.core.0',
        route: null,
        highlight_selector: null,
        nav_selector: null,
        tab_selector: null,
      },
      {
        step: 1,
        i18n_key: 'help.tour.teacher.tracks.auswertungen.steps.0',
        route: '/auswertungen',
        highlight_selector: "[data-testid='auswertungen-exam-table']",
        nav_selector: "[data-testid='nav-auswertungen']",
        tab_selector: null,
      },
    ],
    tracks: [
      {
        id: 'auswertungen',
        i18n_key: 'help.tour.teacher.tracks.auswertungen',
        steps: [
          {
            step: 0,
            i18n_key: 'help.tour.teacher.tracks.auswertungen.steps.0',
            route: '/auswertungen',
            highlight_selector: "[data-testid='auswertungen-exam-table']",
            nav_selector: "[data-testid='nav-auswertungen']",
            tab_selector: null,
          },
        ],
      },
      {
        id: 'einstellungen',
        i18n_key: 'help.tour.teacher.tracks.einstellungen',
        steps: [
          {
            step: 0,
            i18n_key: 'help.tour.teacher.tracks.einstellungen.steps.0',
            route: '/settings/tags',
            highlight_selector: "[data-testid='tag-settings-content']",
            nav_selector: "[data-testid='nav-settings-tags']",
            tab_selector: null,
          },
        ],
      },
    ],
  },
};

const helpContextValue = (overrides: Record<string, unknown> = {}) => ({
  role: 'teacher',
  locale: 'de',
  route: '/',
  helpStatus: { modes: { onboarding: true, context: true, chat: false } },
  onboardingStatus: {
    role: 'teacher',
    current_step: 1,
    completed_steps: [0],
    skipped_steps: [],
    completed: true,
    track_progress: {},
  },
  contextHint: { i18n_key: null, hint_id: null },
  loading: false,
  completeStep: mockCompleteStep,
  skipStep: jest.fn(),
  updateTrackStep: mockUpdateTrackStep,
  trackProgress: {},
  chatAvailable: false,
  showOnboarding: false,
  hasContextHint: false,
  hasSkippedSteps: false,
  ...overrides,
});

const theme = createTheme();

const renderWidget = () =>
  render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <HelpWidget />
      </ThemeProvider>
    </BrowserRouter>,
  );

const openPanel = () =>
  fireEvent.click(screen.getByTestId('help-fab'));

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  const { useHelpContext } = require('../useHelpContext');
  useHelpContext.mockImplementation(() => helpContextValue());
  global.fetch = jest.fn().mockResolvedValue({
    json: () => Promise.resolve(STEPS_FIXTURE),
  }) as any;
});

describe('HelpWidget — Vertiefungen', () => {
  it('zeigt Titel und Beschreibung der Vertiefung, nicht den Schlüssel', async () => {
    renderWidget();
    openPanel();

    const tracks = await screen.findByTestId('help-tracks');
    expect(tracks).toHaveTextContent('Auswertungen');
    expect(tracks.textContent).not.toContain('help.tour.');
  });

  it('bietet Vertiefungen an, obwohl die Kern-Tour abgeschlossen ist', async () => {
    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-tracks')).toBeInTheDocument();
    expect(
      screen.getByTestId('help-track-start-auswertungen'),
    ).toBeInTheDocument();
  });

  it('blendet eine Vertiefung ohne erreichbare Route aus', async () => {
    renderWidget();
    openPanel();

    await screen.findByTestId('help-track-start-auswertungen');
    expect(
      screen.queryByTestId('help-track-start-einstellungen'),
    ).not.toBeInTheDocument();
  });

  it('bleibt bei übersprungenen Kern-Schritten renderstabil (keine Update-Schleife)', async () => {
    // The catch-up effect writes state and depends on the accessibility
    // check. Because the nav hook returns fresh objects per render, an
    // unguarded effect ends up in "Maximum update depth exceeded" here.
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockImplementation(() =>
      helpContextValue({
        onboardingStatus: {
          role: 'teacher',
          current_step: 2,
          completed_steps: [0],
          skipped_steps: [1],
          completed: true,
          track_progress: {},
        },
        hasSkippedSteps: true,
      }),
    );

    renderWidget();
    openPanel();

    expect(
      await screen.findByText(/Neue Seiten wurden freigeschaltet/i),
    ).toBeInTheDocument();

    // useHelpContext is called exactly once per render and therefore acts as
    // a direct render counter. The nav hook above deliberately returns fresh
    // objects per render; without the equality check in the catch-up effect
    // every run writes a new array and the counter runs away.
    const rendersAfterMount = useHelpContext.mock.calls.length;
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 150));
    });
    expect(useHelpContext.mock.calls.length - rendersAfterMount).toBeLessThan(5);
  });

  it('bietet bei angefangener Vertiefung «Fortsetzen» statt «Starten» an', async () => {
    // Otherwise the button describes the wrong action: the tour resumes at
    // step 2, but the label promises a restart.
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockImplementation(() =>
      helpContextValue({
        trackProgress: {
          auswertungen: {
            current_step: 1,
            completed_steps: [0],
            skipped_steps: [],
            completed: false,
          },
        },
      }),
    );

    renderWidget();
    openPanel();

    const button = await screen.findByTestId('help-track-start-auswertungen');
    expect(button).toHaveTextContent(/Fortsetzen/i);
  });

  it('bietet bei unberührter Vertiefung «Starten» an', async () => {
    renderWidget();
    openPanel();

    const button = await screen.findByTestId('help-track-start-auswertungen');
    expect(button).toHaveTextContent(/Starten/i);
  });

  it('führt einen Altbestand-Fortschritt jenseits der neuen Kern-Tour zu Ende', async () => {
    // TF-625 shrinks the admin core tour from 13 to 8 steps. Anyone sitting
    // at current_step=11 in the DB must still be shown the last step —
    // otherwise the tour runs into nothing and never completes.
    const anchor = document.createElement('div');
    anchor.setAttribute('data-testid', 'auswertungen-exam-table');
    document.body.appendChild(anchor);
    window.history.pushState({}, '', '/auswertungen');

    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockImplementation(() =>
      helpContextValue({
        onboardingStatus: {
          role: 'teacher',
          current_step: 11,
          completed_steps: [0],
          skipped_steps: [],
          completed: false,
          track_progress: {},
        },
        showOnboarding: true,
      }),
    );

    try {
      renderWidget();
      openPanel();

      fireEvent.click(
        await screen.findByRole('button', { name: /Tour fortsetzen/i }),
      );

      // The last core step (index 1) is shown, not index 11.
      await waitFor(() => expect(mockHighlight).toHaveBeenCalled());
      fireEvent.click(await screen.findByTestId('onboarding-popover-next'));
      await waitFor(() => expect(mockCompleteStep).toHaveBeenCalledWith(1));
    } finally {
      document.body.removeChild(anchor);
      window.history.pushState({}, '', '/');
    }
  });

  it('zeigt eine abgeschlossene Vertiefung als solche und bietet einen Neustart an', async () => {
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockImplementation(() =>
      helpContextValue({
        trackProgress: {
          auswertungen: {
            current_step: 1,
            completed_steps: [0],
            skipped_steps: [],
            completed: true,
          },
        },
      }),
    );

    renderWidget();
    openPanel();

    const button = await screen.findByTestId('help-track-start-auswertungen');
    expect(button).toHaveTextContent(/Nochmal/i);
  });

  it('schreibt den Fortschritt einer Vertiefung über updateTrackStep, nicht über completeStep', async () => {
    // The deep dive's step points at the route we are already on, so
    // HelpOnboarding goes straight into the spotlight path.
    window.history.pushState({}, '', '/auswertungen');
    const anchor = document.createElement('div');
    anchor.setAttribute('data-testid', 'auswertungen-exam-table');
    document.body.appendChild(anchor);

    try {
      renderWidget();
      openPanel();

      fireEvent.click(await screen.findByTestId('help-track-start-auswertungen'));

      await waitFor(() => expect(mockHighlight).toHaveBeenCalled());

      // Advance via the tour's own popover (rendered by OnboardingPopover,
      // no longer by driver.js).
      fireEvent.click(await screen.findByTestId('onboarding-popover-next'));

      await waitFor(() =>
        expect(mockUpdateTrackStep).toHaveBeenCalledWith('auswertungen', 0, 1, false),
      );
      expect(mockCompleteStep).not.toHaveBeenCalled();
    } finally {
      document.body.removeChild(anchor);
      window.history.pushState({}, '', '/');
    }
  });

  it('markiert keinen Schritt als übersprungen, wenn der Anker vorhanden ist', async () => {
    window.history.pushState({}, '', '/auswertungen');
    const anchor = document.createElement('div');
    anchor.setAttribute('data-testid', 'auswertungen-exam-table');
    document.body.appendChild(anchor);
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});

    try {
      renderWidget();
      openPanel();

      fireEvent.click(await screen.findByTestId('help-track-start-auswertungen'));
      await waitFor(() => expect(mockHighlight).toHaveBeenCalled());

      // TF-604 signature: the skip path logs "[onboarding] Step … skipped".
      expect(
        warn.mock.calls.filter((call) =>
          String(call[0]).includes('[onboarding]'),
        ),
      ).toHaveLength(0);
      expect(mockUpdateTrackStep).not.toHaveBeenCalledWith(
        'auswertungen',
        0,
        1,
        true,
      );
    } finally {
      warn.mockRestore();
      document.body.removeChild(anchor);
      window.history.pushState({}, '', '/');
    }
  });
});

/**
 * A deep dive unlocked after the core tour was finished was only discoverable
 * by opening the panel on spec: the catch-up banner covers the core tour's
 * skipped steps, but never saw the deep dives.
 */
describe('HelpWidget — neu freigeschaltete Vertiefungen', () => {
  it('markiert eine noch nie gezeigte Vertiefung als neu', async () => {
    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-track-new-auswertungen')).toBeInTheDocument();
  });

  it('markiert nichts, was der Nutzer schon gesehen hat', async () => {
    localStorage.setItem('examcraft.help.seenTracks', JSON.stringify(['auswertungen']));

    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-tracks')).toBeInTheDocument();
    expect(screen.queryByTestId('help-track-new-auswertungen')).not.toBeInTheDocument();
  });

  /**
   * On close, not on render: marking them as the pane appears made the chip
   * vanish in the frame it was drawn.
   */
  it('merkt sich erst beim Schliessen, was gezeigt wurde', async () => {
    renderWidget();
    openPanel();

    await screen.findByTestId('help-track-new-auswertungen');
    expect(JSON.parse(localStorage.getItem('examcraft.help.seenTracks') || '[]')).toEqual([]);

    fireEvent.click(screen.getByRole('button', { name: /close/i }));

    await waitFor(() =>
      expect(
        JSON.parse(localStorage.getItem('examcraft.help.seenTracks') || '[]'),
      ).toContain('auswertungen'),
    );
  });

  it('markiert nichts, solange die Kern-Tour noch offen ist', async () => {
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockImplementation(() =>
      helpContextValue({
        showOnboarding: true,
        onboardingStatus: {
          role: 'teacher',
          current_step: 1,
          completed_steps: [0],
          skipped_steps: [],
          completed: false,
          track_progress: {},
        },
      }),
    );

    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-tracks')).toBeInTheDocument();
    expect(screen.queryByTestId('help-track-new-auswertungen')).not.toBeInTheDocument();
  });

  it('zeigt den Punkt am Hilfe-Knopf, solange etwas Neues wartet', async () => {
    renderWidget();

    // Panel closed: the badge is the only signal there is. MUI hides the dot
    // with a class rather than by unmounting it, and Testing Library has no
    // query for "is this badge showing" — hence the direct lookup.
    const badge = await screen.findByTestId('help-fab-badge');
    await waitFor(() =>
      expect(
        // eslint-disable-next-line testing-library/no-node-access
        badge.querySelector('.MuiBadge-invisible'),
      ).not.toBeInTheDocument(),
    );
  });
});

describe('HelpWidget — Kern-Tour wiederholen', () => {
  /**
   * The deep dives always offered "Nochmal"; the core tour did not, because
   * its start/resume banner is gated on `showOnboarding`, which goes false the
   * moment the tour completes. Reported from the field: "ich kann alle Touren
   * nochmal durchspielen, aber nicht die erste Haupt-Tour".
   */
  it('bietet die abgeschlossene Kern-Tour zum Wiederholen an', async () => {
    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-core-tour-replay')).toBeInTheDocument();
  });

  /**
   * Not index 0: the welcome step carries neither route nor selector, so
   * entering it ends the tour immediately — clicking "Nochmal" showed nothing
   * but the "tour complete" panel. On a first run the tour never sees that
   * step (OnboardingModal shows it, handleStartTour completes it beforehand).
   * Caught in the browser after the first version of this test asserted the
   * broken behaviour.
   */
  it('startet die Wiederholung beim ersten Schritt mit Inhalt, nicht beim Willkommens-Schritt', async () => {
    const navAnchor = document.createElement('a');
    navAnchor.setAttribute('data-testid', 'nav-auswertungen');
    document.body.appendChild(navAnchor);

    try {
      renderWidget();
      openPanel();

      fireEvent.click(await screen.findByTestId('help-core-tour-replay'));

      // Fixture core steps: 0 = welcome (no route/selector), 1 = Auswertungen.
      await waitFor(() =>
        expect(mockHighlight).toHaveBeenCalledWith(
          expect.objectContaining({ element: "[data-testid='nav-auswertungen']" }),
        ),
      );
      expect(mockCompleteStep).not.toHaveBeenCalledWith(0);
    } finally {
      document.body.removeChild(navAnchor);
    }
  });

  it('legt Kern-Tour und Vertiefungen in denselben Bereich', async () => {
    renderWidget();
    openPanel();

    const tours = await screen.findByTestId('help-tours');
    expect(tours).toContainElement(screen.getByTestId('help-core-tour-replay'));
    expect(tours).toContainElement(screen.getByTestId('help-tracks'));
  });

  it('zeigt die Wiederholung nicht an, solange die Tour noch offen ist', async () => {
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockImplementation(() =>
      helpContextValue({
        showOnboarding: true,
        onboardingStatus: {
          role: 'teacher',
          current_step: 1,
          completed_steps: [0],
          skipped_steps: [],
          completed: false,
          track_progress: {},
        },
      }),
    );

    renderWidget();
    openPanel();

    // The tracks list confirms the panel rendered at all.
    expect(await screen.findByTestId('help-tracks')).toBeInTheDocument();
    expect(screen.queryByTestId('help-core-tour-replay')).not.toBeInTheDocument();
  });
});

/**
 * Tours and chat used to be stacked in one column and competed for the panel's
 * height. With five deep dives, the core-tour row and a page hint above them,
 * the chat input ended up below the panel edge — reported as "I can't see the
 * text field at all". They are two panes behind a tab strip now, so each gets
 * the full height.
 */
describe('HelpWidget — Touren und Chat als getrennte Bereiche', () => {
  const withChat = (overrides: Record<string, unknown> = {}) => {
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockImplementation(() =>
      helpContextValue({ chatAvailable: true, ...overrides }),
    );
  };

  it('trennt Touren und Chat in zwei Reiter, wenn beide etwas zu zeigen haben', async () => {
    withChat();
    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-tab-tours')).toBeInTheDocument();
    expect(screen.getByTestId('help-tab-chat')).toBeInTheDocument();
  });

  it('zeigt immer nur einen der beiden Bereiche', async () => {
    withChat();
    renderWidget();
    openPanel();

    // The steps arrive by fetch — wait for the tabs before judging the panes.
    await screen.findByTestId('help-tab-tours');

    // Core tour is complete in the fixture, so the chat is the landing pane,
    // with no frame of the tours pane in between.
    expect(screen.getByTestId('help-chat-stub')).toBeInTheDocument();
    expect(screen.queryByTestId('help-tours-pane')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('help-tab-tours'));

    expect(await screen.findByTestId('help-tours-pane')).toBeInTheDocument();
    expect(screen.queryByTestId('help-chat-stub')).not.toBeInTheDocument();
  });

  it('landet auf den Touren, solange die Einführungstour offen ist', async () => {
    withChat({
      showOnboarding: true,
      onboardingStatus: {
        role: 'teacher',
        current_step: 1,
        completed_steps: [0],
        skipped_steps: [],
        completed: false,
        track_progress: {},
      },
    });
    localStorage.setItem('ec_onboarding_modal_dismissed', 'true');

    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-tours-pane')).toBeInTheDocument();
    expect(screen.queryByTestId('help-chat-stub')).not.toBeInTheDocument();
  });

  it('merkt sich den zuletzt gewählten Bereich über das Schliessen hinaus', async () => {
    withChat();
    const { unmount } = renderWidget();
    openPanel();

    await screen.findByTestId('help-tab-tours');
    fireEvent.click(screen.getByTestId('help-tab-tours'));
    expect(await screen.findByTestId('help-tours-pane')).toBeInTheDocument();

    // Close, and reopen from scratch — a fresh mount, as after a reload.
    fireEvent.click(screen.getByTestId('help-fab'));
    unmount();

    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-tours-pane')).toBeInTheDocument();
    expect(screen.queryByTestId('help-chat-stub')).not.toBeInTheDocument();
  });

  /**
   * Reported: finishing a deep dive reopened the panel on the chat. Only the
   * core tour set `tourJustCompleted`, which was the single tours signal the
   * default consulted — a finished track had none.
   */
  it('landet nach dem Ende einer Vertiefung auf den Touren', async () => {
    withChat();
    const anchor = document.createElement('div');
    anchor.setAttribute('data-testid', 'auswertungen-exam-table');
    document.body.appendChild(anchor);
    window.history.pushState({}, '', '/auswertungen');

    try {
      renderWidget();
      openPanel();

      // Land on the chat first, so the assertion cannot pass by default.
      await screen.findByTestId('help-tab-chat');
      expect(screen.getByTestId('help-chat-stub')).toBeInTheDocument();

      fireEvent.click(screen.getByTestId('help-tab-tours'));
      fireEvent.click(await screen.findByTestId('help-track-start-auswertungen'));
      fireEvent.click(screen.getByTestId('help-tab-chat'));

      // The single-step track finishes on the first "Fertig".
      await waitFor(() => expect(mockHighlight).toHaveBeenCalled());
      fireEvent.click(await screen.findByTestId('onboarding-popover-next'));

      expect(await screen.findByTestId('help-tours-pane')).toBeInTheDocument();
      expect(screen.queryByTestId('help-chat-stub')).not.toBeInTheDocument();
    } finally {
      document.body.removeChild(anchor);
      window.history.pushState({}, '', '/');
    }
  });

  it('kommt ohne Reiter aus, wenn es nur einen Bereich gibt', async () => {
    // Fixture default: chatAvailable false — tours only.
    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-tracks')).toBeInTheDocument();
    expect(screen.queryByTestId('help-tab-tours')).not.toBeInTheDocument();
    expect(screen.queryByTestId('help-tab-chat')).not.toBeInTheDocument();
  });

  it('zeigt den Chat ohne Reiter, wenn es keine Touren gibt', async () => {
    withChat();
    // No core tour steps and no tracks -> nothing for a tours pane.
    global.fetch = jest.fn().mockResolvedValue({
      json: () => Promise.resolve({ teacher: { core: [], tracks: [] } }),
    }) as any;

    renderWidget();
    openPanel();

    expect(await screen.findByTestId('help-chat-stub')).toBeInTheDocument();
    expect(screen.queryByTestId('help-tab-chat')).not.toBeInTheDocument();
  });
});

