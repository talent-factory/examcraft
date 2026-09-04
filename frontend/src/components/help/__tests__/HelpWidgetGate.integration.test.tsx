/**
 * HelpWidgetGate — integration with the real HelpWidget (TF-657).
 *
 * Complement to HelpWidgetGate.test.tsx, where `HelpWidget` is stubbed: that
 * test only checks the gate's branching. All other TF-657 tests are negative
 * assertions ("no FAB on /login") — those would still pass even if the widget
 * accidentally dropped out of the tree entirely.
 *
 * This test is the counter-check: the *real* HelpWidget must render its FAB
 * through the gate. Only `useHelpContext` is mocked (as in HelpWidget.test.tsx)
 * so no help requests are needed.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { BrowserRouter } from 'react-router-dom';
import HelpWidgetGate from '../HelpWidgetGate';

const mockUseAuth = jest.fn();

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('../useHelpContext', () => ({
  useHelpContext: jest.fn(() => ({
    role: 'teacher',
    locale: 'de',
    route: '/dashboard',
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
    chatAvailable: false,
    showOnboarding: false,
    hasContextHint: false,
    hasSkippedSteps: false,
  })),
}));

const theme = createTheme();

const renderGate = () =>
  render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <HelpWidgetGate />
      </ThemeProvider>
    </BrowserRouter>
  );

describe('HelpWidgetGate — echtes HelpWidget', () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
  });

  it('rendert den FAB des echten HelpWidget wenn authentifiziert', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });

    renderGate();

    expect(screen.getByTestId('help-fab')).toBeInTheDocument();
  });

  it('unterdrückt den FAB des echten HelpWidget wenn nicht authentifiziert', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });

    renderGate();

    expect(screen.queryByTestId('help-fab')).not.toBeInTheDocument();
  });
});
