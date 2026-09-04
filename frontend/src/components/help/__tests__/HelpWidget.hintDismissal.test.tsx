import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { BrowserRouter } from 'react-router-dom';
// Safe above the mock factories below: they read `mockAcknowledgeHint` when the
// hook renders, not when the factory runs, so there is no dead-zone hit.
import HelpWidget from '../HelpWidget';

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, roles: [{ name: 'teacher' }], institution: null },
    accessToken: 'test-token',
    hasRole: (role: string) => role === 'teacher',
    hasPermission: () => true,
  }),
}));

const mockAcknowledgeHint = jest.fn();
const mockDismissHint = jest.fn().mockResolvedValue(undefined);

jest.mock('../../../services/HelpService', () => ({
  helpService: { dismissHint: (...args: unknown[]) => mockDismissHint(...args) },
}));

jest.mock('../useHelpContext', () => ({
  useHelpContext: jest.fn(() => ({
    role: 'teacher',
    locale: 'de',
    route: '/exams/compose',
    helpStatus: { modes: { onboarding: true, context: true, chat: false } },
    onboardingStatus: {
      role: 'teacher',
      current_step: 8,
      completed_steps: [0, 1, 2, 3, 4, 5, 6, 7],
      skipped_steps: [],
      completed: true,
    },
    // A key, not a text — the component resolves it, and setupTests resolves
    // keys against the real de/translation.json, so the assertions below also
    // prove the key exists there.
    contextHint: { i18n_key: 'help.hints.examsCompose', hint_id: 6 },
    loading: false,
    completeStep: jest.fn(),
    skipStep: jest.fn(),
    updateTrackStep: jest.fn(),
    trackProgress: {},
    chatAvailable: false,
    showOnboarding: false,
    hasContextHint: true,
    hasSkippedSteps: false,
    acknowledgeHint: mockAcknowledgeHint,
  })),
}));

const theme = createTheme();

const renderWidget = () =>
  render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <HelpWidget />
      </ThemeProvider>
    </BrowserRouter>
  );

const openPanel = () => fireEvent.click(screen.getByRole('button', { name: /hilfe/i }));
const expandHint = () => fireEvent.click(screen.getByTestId('help-context-hint-toggle'));

beforeEach(() => {
  mockAcknowledgeHint.mockClear();
  mockDismissHint.mockClear();
});

/**
 * Nothing retires a hint on the user's behalf. Merely looking at it — or
 * opening the panel it lives in — must not count as a decision.
 */
describe('HelpWidget context hint dismissal', () => {
  it('does not acknowledge the hint just because it was displayed', () => {
    renderWidget();
    openPanel();
    expect(screen.getByText(/Hier erscheinen nur geprüfte Fragen/)).toBeVisible();
    expect(mockAcknowledgeHint).not.toHaveBeenCalled();
  });

  it('acknowledges the hint when the user clicks "Verstanden"', () => {
    renderWidget();
    openPanel();
    expandHint();
    fireEvent.click(screen.getByRole('button', { name: /verstanden/i }));
    expect(mockAcknowledgeHint).toHaveBeenCalledWith(6);
    expect(mockDismissHint).not.toHaveBeenCalled();
  });

  it('"Nicht mehr anzeigen" also tells the server, so it outlives the tab', async () => {
    renderWidget();
    openPanel();
    expandHint();
    fireEvent.click(screen.getByRole('button', { name: /nicht mehr anzeigen/i }));
    await waitFor(() => expect(mockDismissHint).toHaveBeenCalledWith('test-token', 6));
    // The local hide runs after the awaited server call, so it needs its own wait.
    await waitFor(() => expect(mockAcknowledgeHint).toHaveBeenCalledWith(6));
  });
});
