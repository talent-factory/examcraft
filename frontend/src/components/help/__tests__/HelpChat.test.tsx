import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

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
  'help.send': 'Senden',
  'help.thinking': 'Denke nach…',
};

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => translations[key] ?? fallback ?? key,
    i18n: { language: 'de' },
  }),
}));

import HelpChat from '../HelpChat';
import { helpService } from '../../../services/HelpService';

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

    await act(async () => {
      fireEvent.keyDown(input, { key: 'Enter' });
    });

    expect(screen.queryByText(/Denke nach/i)).not.toBeInTheDocument();
    expect(screen.getByText('Hier ist die Antwort.')).toBeInTheDocument();
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

    await act(async () => {
      fireEvent.keyDown(input, { key: 'Enter' });
    });

    const saved = JSON.parse(sessionStorage.getItem('ec_help_chat_messages') || '[]');
    expect(saved).toHaveLength(2);
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

    await act(async () => {
      fireEvent.keyDown(input, { key: 'Enter' });
    });

    fireEvent.click(screen.getByRole('button', { name: /Neue Konversation/i }));

    expect(sessionStorage.getItem('ec_help_chat_messages')).toBeNull();
    expect(screen.queryByText('Frage')).not.toBeInTheDocument();
  });
});
