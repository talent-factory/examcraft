import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import HelpChat from '../HelpChat';
import { helpService } from '../../../services/HelpService';
import { AppError } from '../../../errors';

// jsdom does not implement scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn();

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ accessToken: 'test-token' }),
}));

jest.mock('../../../services/HelpService', () => ({
  helpService: {
    sendMessage: jest.fn(),
  },
}));

const translations: Record<string, string> = {
  'help.chatPlaceholder': 'Stelle eine Frage...',
  'help.newConversation': 'Neue Konversation',
  'help.chatUnavailable': 'Der Hilfe-Chat ist derzeit nicht verfügbar.',
  'help.rateLimited': 'Du hast das Fragelimit erreicht. Bitte versuche es später erneut.',
  'help.sessionExpired': 'Deine Sitzung ist abgelaufen. Bitte lade die Seite neu.',
  'help.thinking': 'Denke nach…',
  'errors.help_rate_limit_exceeded': 'Limit erreicht: maximal 20 Hilfe-Fragen pro Stunde',
  'errors.help_message_failed': 'Deine Frage konnte nicht gesendet werden.',
};

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    // translateError passes interpolation params as the second argument, so
    // only a string counts as a default value.
    t: (key: string, fallback?: unknown) =>
      translations[key] ?? (typeof fallback === 'string' ? fallback : key),
    i18n: { language: 'de' },
  }),
}));

const theme = createTheme();
const renderChat = () =>
  render(
    <ThemeProvider theme={theme}>
      <HelpChat route="/" />
    </ThemeProvider>
  );

describe('HelpChat — Loading-Indikator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('zeigt pulsierenden Punkt mit Text wenn Bot antwortet', async () => {
    (helpService.sendMessage as jest.Mock).mockReturnValue(new Promise(() => {}));

    renderChat();

    const input = screen.getByPlaceholderText(/Stelle eine Frage/i);
    fireEvent.change(input, { target: { value: 'Wie geht das?' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(await screen.findByText(/Denke nach/i)).toBeInTheDocument();
  });

  it('versteckt Loading-Indikator nach Antwort', async () => {
    (helpService.sendMessage as jest.Mock).mockResolvedValue({
      answer: 'Hier ist die Antwort.',
      confidence: 0.9,
      sources: [],
    });

    renderChat();

    const input = screen.getByPlaceholderText(/Stelle eine Frage/i);
    fireEvent.change(input, { target: { value: 'Test?' } });

    fireEvent.keyDown(input, { key: 'Enter' });

    expect(await screen.findByText('Hier ist die Antwort.')).toBeInTheDocument();
    expect(screen.queryByText(/Denke nach/i)).not.toBeInTheDocument();
  });
});

describe('HelpChat — sessionStorage Persistenz', () => {
  beforeEach(() => {
    sessionStorage.clear();
    jest.clearAllMocks();
  });

  it('lädt bestehende Messages aus sessionStorage beim Mount', () => {
    const stored = [
      { role: 'user', content: 'Hallo' },
      { role: 'assistant', content: 'Wie kann ich helfen?' },
    ];
    sessionStorage.setItem('ec_help_chat_messages', JSON.stringify(stored));

    renderChat();

    expect(screen.getByText('Hallo')).toBeInTheDocument();
    expect(screen.getByText('Wie kann ich helfen?')).toBeInTheDocument();
  });

  it('speichert neue Messages in sessionStorage', async () => {
    (helpService.sendMessage as jest.Mock).mockResolvedValue({
      answer: 'Die Antwort.',
      confidence: 0.9,
      sources: [],
    });

    renderChat();

    const input = screen.getByPlaceholderText(/Stelle eine Frage/i);
    fireEvent.change(input, { target: { value: 'Meine Frage' } });

    fireEvent.keyDown(input, { key: 'Enter' });

    // The persistence effect runs after the answer is committed, so wait on
    // the stored array itself rather than on the rendered answer text.
    const readSaved = () => JSON.parse(sessionStorage.getItem('ec_help_chat_messages') || '[]');
    await waitFor(() => expect(readSaved()).toHaveLength(2));
    const saved = readSaved();
    expect(saved[0]).toMatchObject({ role: 'user', content: 'Meine Frage' });
    expect(saved[1]).toMatchObject({ role: 'assistant', content: 'Die Antwort.' });
  });

  it('leert sessionStorage beim Klick auf "Neue Konversation"', async () => {
    (helpService.sendMessage as jest.Mock).mockResolvedValue({
      answer: 'Antwort.',
      confidence: 0.9,
      sources: [],
    });

    renderChat();

    const input = screen.getByPlaceholderText(/Stelle eine Frage/i);
    fireEvent.change(input, { target: { value: 'Frage' } });

    fireEvent.keyDown(input, { key: 'Enter' });
    await screen.findByText('Antwort.');

    fireEvent.click(screen.getByRole('button', { name: /Neue Konversation/i }));

    expect(sessionStorage.getItem('ec_help_chat_messages')).toBeNull();
    expect(screen.queryByText('Frage')).not.toBeInTheDocument();
  });
});

describe('HelpChat — KI-Kennzeichnung (EU AI Act Art. 50, TF-747)', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('weist darauf hin, dass mit einem KI-System gechattet wird', () => {
    renderChat();
    expect(screen.getByTestId('ai-notice-chat')).toBeInTheDocument();
  });
});

describe('HelpChat — Fehlermeldungen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const ask = async () => {
    renderChat();
    const input = screen.getByPlaceholderText(/Stelle eine Frage/i);
    fireEvent.change(input, { target: { value: 'Wie geht das?' } });
    fireEvent.keyDown(input, { key: 'Enter' });
  };

  it('zeigt bei 429 mit Backend-Code dessen Satz mit Limit und Zeitfenster', async () => {
    (helpService.sendMessage as jest.Mock).mockRejectedValue(
      new AppError('help_rate_limit_exceeded', 'Rate limit', 429)
    );

    await ask();

    expect(
      await screen.findByText('Limit erreicht: maximal 20 Hilfe-Fragen pro Stunde')
    ).toBeInTheDocument();
    expect(screen.queryByText(/Fragelimit erreicht/)).not.toBeInTheDocument();
  });

  it('bleibt bei 429 ohne Backend-Code (IP-Limiter) beim allgemeinen Satz', async () => {
    // HelpService turns a code-less response into its operation fallback.
    (helpService.sendMessage as jest.Mock).mockRejectedValue(
      new AppError('help_message_failed', 'HTTP 429', 429)
    );

    await ask();

    expect(
      await screen.findByText('Du hast das Fragelimit erreicht. Bitte versuche es später erneut.')
    ).toBeInTheDocument();
    expect(screen.queryByText('Deine Frage konnte nicht gesendet werden.')).not.toBeInTheDocument();
  });

  it('zeigt bei anderen Fehlern weiterhin den Nicht-verfügbar-Satz', async () => {
    (helpService.sendMessage as jest.Mock).mockRejectedValue(
      new AppError('help_message_failed', 'HTTP 500', 500)
    );

    await ask();

    expect(
      await screen.findByText('Der Hilfe-Chat ist derzeit nicht verfügbar.')
    ).toBeInTheDocument();
  });
});
