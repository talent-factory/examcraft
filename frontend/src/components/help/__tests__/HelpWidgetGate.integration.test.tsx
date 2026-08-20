/**
 * HelpWidgetGate — Integration mit dem echten HelpWidget (TF-657).
 *
 * Ergänzung zu HelpWidgetGate.test.tsx, wo `HelpWidget` gestubbt ist: dort wird
 * nur die Verzweigung des Gates geprüft. Alle übrigen Tests zu TF-657 sind
 * Negativ-Assertions („kein FAB auf /login") — die wären auch dann grün, wenn
 * das Widget versehentlich ganz aus dem Baum fiele.
 *
 * Dieser Test ist die Gegenprobe: das *echte* HelpWidget muss durch das Gate
 * hindurch seinen FAB rendern. Gemockt wird nur `useHelpContext` (wie in
 * HelpWidget.test.tsx), damit keine Help-Requests nötig sind.
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
    contextHint: { hint_text: null, hint_id: null },
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
