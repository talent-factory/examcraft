import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { BrowserRouter } from 'react-router-dom';

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, roles: [{ name: 'teacher' }], institution: null },
    accessToken: 'test-token',
    hasRole: (role: string) => role === 'teacher',
    // TF-625: HelpWidget uses useRoleBasedNavigation to hide deep dives with
    // no reachable route — that hook calls hasPermission.
    hasPermission: () => true,
  }),
}));

jest.mock('../useHelpContext', () => ({
  useHelpContext: jest.fn(() => ({
    role: 'teacher',
    locale: 'de',
    route: '/',
    helpStatus: { modes: { onboarding: true, context: true, chat: false } },
    onboardingStatus: {
      role: 'teacher',
      current_step: 5,
      completed_steps: [0, 1, 2, 3, 4],
      skipped_steps: [],
      completed: true,
    },
    contextHint: { i18n_key: null, hint_id: null },
    loading: false,
    completeStep: jest.fn(),
    skipStep: jest.fn(),
    updateTrackStep: jest.fn(),
    trackProgress: {},
    chatAvailable: false,
    showOnboarding: false,
    hasContextHint: false,
    hasSkippedSteps: false,
  })),
}));

import HelpWidget, { clampPanelDimension } from '../HelpWidget';

const theme = createTheme();

const renderWidget = () =>
  render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <HelpWidget />
      </ThemeProvider>
    </BrowserRouter>
  );

describe('HelpWidget', () => {
  it('renders the floating help button', () => {
    renderWidget();
    expect(screen.getByRole('button', { name: /hilfe/i })).toBeInTheDocument();
  });
});

describe('HelpWidget — clampPanelDimension (panel resize)', () => {
  it('clamps to a value within [min, max] under normal conditions', () => {
    expect(clampPanelDimension(360, 800, 500)).toBe(500);
    expect(clampPanelDimension(360, 800, 1000)).toBe(800);
    expect(clampPanelDimension(360, 800, 100)).toBe(360);
  });

  it('does not exceed max even when max < min (viewport smaller than the preferred minimum)', () => {
    // The exact regression this clamp exists to fix: a window shorter than
    // MIN_HEIGHT + PANEL_VERTICAL_MARGIN makes MAX_HEIGHT < MIN_HEIGHT. The
    // naive `Math.max(min, Math.min(max, value))` would return `min` (520)
    // here regardless of `value`, overflowing the 480px actually available.
    expect(clampPanelDimension(520, 480, 1000)).toBe(480);
    expect(clampPanelDimension(520, 480, 0)).toBe(480);
    expect(clampPanelDimension(520, 480, 480)).toBe(480);
  });

  it('is idempotent (clamping an already-clamped value returns it unchanged)', () => {
    const once = clampPanelDimension(360, 800, 900);
    expect(clampPanelDimension(360, 800, once)).toBe(once);
  });
});

describe('HelpWidget — Catch-up Banner', () => {
  it('zeigt keinen Banner wenn skipped_steps leer ist', () => {
    renderWidget();
    expect(
      screen.queryByText(/Neue Seiten wurden freigeschaltet/i)
    ).not.toBeInTheDocument();
  });
});

describe('HelpWidget — Modal-Persistenz', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockReset();
    useHelpContext.mockImplementation(() => ({
      role: 'teacher',
      locale: 'de',
      route: '/',
      helpStatus: { modes: { onboarding: true, context: true, chat: false } },
      onboardingStatus: {
        role: 'teacher',
        current_step: 5,
        completed_steps: [0, 1, 2, 3, 4],
        skipped_steps: [],
        completed: true,
      },
      contextHint: { i18n_key: null, hint_id: null },
      loading: false,
      completeStep: jest.fn(),
      skipStep: jest.fn(),
      updateTrackStep: jest.fn(),
      trackProgress: {},
      chatAvailable: false,
      showOnboarding: false,
      hasContextHint: false,
      hasSkippedSteps: false,
    }));
  });

  it('zeigt Modal nicht wenn ec_onboarding_modal_dismissed gesetzt ist', () => {
    localStorage.setItem('ec_onboarding_modal_dismissed', 'true');

    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockReturnValueOnce({
      role: 'teacher',
      locale: 'de',
      route: '/',
      helpStatus: { modes: { onboarding: true, context: true, chat: false } },
      onboardingStatus: {
        role: 'teacher',
        current_step: 0,
        completed_steps: [],
        skipped_steps: [],
        completed: false,
      },
      contextHint: { i18n_key: null, hint_id: null },
      loading: false,
      completeStep: jest.fn(),
      skipStep: jest.fn(),
      updateTrackStep: jest.fn(),
      trackProgress: {},
      chatAvailable: false,
      showOnboarding: true,
      hasContextHint: false,
      hasSkippedSteps: false,
    });

    renderWidget();
    expect(screen.queryByRole('button', { name: /Tour starten/i })).not.toBeInTheDocument();
  });

  it('setzt localStorage-Key wenn "Später" geklickt wird', async () => {
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockReturnValue({
      role: 'teacher',
      locale: 'de',
      route: '/',
      helpStatus: { modes: { onboarding: true, context: true, chat: false } },
      onboardingStatus: {
        role: 'teacher',
        current_step: 0,
        completed_steps: [],
        skipped_steps: [],
        completed: false,
      },
      contextHint: { i18n_key: null, hint_id: null },
      loading: false,
      completeStep: jest.fn(),
      skipStep: jest.fn(),
      updateTrackStep: jest.fn(),
      trackProgress: {},
      chatAvailable: false,
      showOnboarding: true,
      hasContextHint: false,
      hasSkippedSteps: false,
    });

    global.fetch = jest.fn().mockResolvedValue({
      json: () => Promise.resolve({
        teacher: {
          core: [{ step: 0, i18n_key: 'help.tour.teacher.core.0', route: null, highlight_selector: null, nav_selector: null, tab_selector: null }],
          tracks: [],
        },
      }),
    } as any);

    renderWidget();

    await screen.findByRole('button', { name: /Später/i });
    fireEvent.click(screen.getByRole('button', { name: /Später/i }));

    expect(localStorage.getItem('ec_onboarding_modal_dismissed')).toBe('true');
  });
});

describe('HelpWidget — Tour-Banner', () => {
  afterEach(() => {
    if (typeof localStorage !== 'undefined') {
      localStorage.clear();
    }
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockReset();
    useHelpContext.mockImplementation(() => ({
      role: 'teacher',
      locale: 'de',
      route: '/',
      helpStatus: { modes: { onboarding: true, context: true, chat: false } },
      onboardingStatus: {
        role: 'teacher',
        current_step: 5,
        completed_steps: [0, 1, 2, 3, 4],
        skipped_steps: [],
        completed: true,
      },
      contextHint: { i18n_key: null, hint_id: null },
      loading: false,
      completeStep: jest.fn(),
      skipStep: jest.fn(),
      updateTrackStep: jest.fn(),
      trackProgress: {},
      chatAvailable: false,
      showOnboarding: false,
      hasContextHint: false,
      hasSkippedSteps: false,
    }));
  });

  const renderWithOnboarding = (current_step: number) => {
    const { useHelpContext } = require('../useHelpContext');
    useHelpContext.mockReturnValue({
      role: 'teacher',
      locale: 'de',
      route: '/',
      helpStatus: { modes: { onboarding: true, context: true, chat: false } },
      onboardingStatus: {
        role: 'teacher',
        current_step,
        completed_steps: Array.from({ length: current_step }, (_, i) => i),
        skipped_steps: [],
        completed: false,
      },
      contextHint: { i18n_key: null, hint_id: null },
      loading: false,
      completeStep: jest.fn().mockResolvedValue(undefined),
      skipStep: jest.fn(),
      updateTrackStep: jest.fn(),
      trackProgress: {},
      chatAvailable: false,
      showOnboarding: true,
      hasContextHint: false,
      hasSkippedSteps: false,
    });

    global.fetch = jest.fn().mockResolvedValue({
      json: () => Promise.resolve({
        teacher: {
          core: [
            { step: 0, i18n_key: 'help.tour.teacher.core.0', route: null, highlight_selector: null, nav_selector: null, tab_selector: null },
            { step: 1, i18n_key: 'help.tour.teacher.core.1', route: '/documents', highlight_selector: '[data-testid="x"]', nav_selector: null, tab_selector: null },
          ],
          tracks: [],
        },
      }),
    } as any);

    return renderWidget();
  };

  it('zeigt "Tour starten" Button wenn current_step === 0', async () => {
    renderWithOnboarding(0);
    fireEvent.click(screen.getByRole('button', { name: /hilfe/i }));
    expect(await screen.findByRole('button', { name: /Tour starten/i })).toBeInTheDocument();
  });

  it('zeigt "Tour fortsetzen" Button wenn current_step > 0', async () => {
    renderWithOnboarding(1);
    fireEvent.click(screen.getByRole('button', { name: /hilfe/i }));
    expect(await screen.findByRole('button', { name: /Tour fortsetzen/i })).toBeInTheDocument();
  });
});
