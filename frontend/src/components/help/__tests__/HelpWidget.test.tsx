import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { BrowserRouter } from 'react-router-dom';

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, roles: [{ name: 'teacher' }], institution: null },
    accessToken: 'test-token',
    hasRole: (role: string) => role === 'teacher',
  }),
}));

jest.mock('../useHelpContext', () => ({
  useHelpContext: () => ({
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
    contextHint: { hint_text: null, hint_id: null },
    loading: false,
    completeStep: jest.fn(),
    skipStep: jest.fn(),
    chatAvailable: false,
    showOnboarding: false,
    hasContextHint: false,
    hasSkippedSteps: false,
  }),
}));

import HelpWidget from '../HelpWidget';

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

describe('HelpWidget — Catch-up Banner', () => {
  it('zeigt keinen Banner wenn skipped_steps leer ist', () => {
    renderWidget();
    expect(
      screen.queryByText(/Neue Seiten wurden freigeschaltet/i)
    ).not.toBeInTheDocument();
  });
});
