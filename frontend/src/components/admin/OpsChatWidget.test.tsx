import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import OpsChatWidget from './OpsChatWidget';
import * as opsChatService from '../../services/opsChatService';

// jsdom does not implement scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn();

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('OpsChatWidget', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  const typeAndSend = (text: string) => {
    fireEvent.change(screen.getByLabelText('pages.admin.systemHealth.chat.inputLabel'), {
      target: { value: text },
    });
    fireEvent.click(screen.getByText('pages.admin.systemHealth.chat.send'));
  };

  it('sends a message and renders both the user turn and the assistant reply', async () => {
    const sendSpy = jest
      .spyOn(opsChatService, 'sendOpsChatMessage')
      .mockResolvedValue('Celery hat 2 aktive Worker.');

    render(<OpsChatWidget />);
    typeAndSend('Wie viele Celery-Worker laufen?');

    expect(await screen.findByText('Wie viele Celery-Worker laufen?')).toBeInTheDocument();
    expect(await screen.findByText('Celery hat 2 aktive Worker.')).toBeInTheDocument();
    expect(sendSpy).toHaveBeenCalledWith('Wie viele Celery-Worker laufen?', []);
  });

  it('sends the prior turns as history on the second message', async () => {
    const sendSpy = jest
      .spyOn(opsChatService, 'sendOpsChatMessage')
      .mockResolvedValueOnce('Erste Antwort.')
      .mockResolvedValueOnce('Zweite Antwort.');

    render(<OpsChatWidget />);
    typeAndSend('Erste Frage');
    await screen.findByText('Erste Antwort.');

    typeAndSend('Zweite Frage');
    await screen.findByText('Zweite Antwort.');

    expect(sendSpy).toHaveBeenNthCalledWith(2, 'Zweite Frage', [
      { role: 'user', content: 'Erste Frage' },
      { role: 'assistant', content: 'Erste Antwort.' },
    ]);
  });

  it('shows an error alert when the request fails', async () => {
    jest.spyOn(opsChatService, 'sendOpsChatMessage').mockRejectedValue(new Error('network down'));

    render(<OpsChatWidget />);
    typeAndSend('Frage');

    expect(await screen.findByTestId('ops-chat-error')).toBeInTheDocument();
  });

  it('does not send an empty message', () => {
    const sendSpy = jest.spyOn(opsChatService, 'sendOpsChatMessage');

    render(<OpsChatWidget />);
    fireEvent.click(screen.getByText('pages.admin.systemHealth.chat.send'));

    expect(sendSpy).not.toHaveBeenCalled();
  });

  it('disables input and Send while a request is in flight, and ignores a second click', async () => {
    let resolveSend: (value: string) => void = () => {};
    const pending = new Promise<string>((resolve) => {
      resolveSend = resolve;
    });
    const sendSpy = jest.spyOn(opsChatService, 'sendOpsChatMessage').mockReturnValue(pending);

    render(<OpsChatWidget />);
    const textbox = screen.getByLabelText('pages.admin.systemHealth.chat.inputLabel');
    fireEvent.change(textbox, { target: { value: 'Frage' } });
    const sendButton = screen.getByRole('button');
    fireEvent.click(sendButton);

    expect(textbox).toBeDisabled();
    expect(sendButton).toBeDisabled();

    // A second click while the request is still pending must not fire a second call.
    fireEvent.click(sendButton);
    expect(sendSpy).toHaveBeenCalledTimes(1);

    resolveSend('Antwort.');
    expect(await screen.findByText('Antwort.')).toBeInTheDocument();
    // Input is cleared on send, so the button stays disabled afterwards for
    // an unrelated reason (empty input) — the textbox re-enabling is what
    // proves `loading` was reset.
    expect(textbox).not.toBeDisabled();
  });

  it('renders the assistant reply as Markdown while the user turn stays plain text', async () => {
    jest
      .spyOn(opsChatService, 'sendOpsChatMessage')
      .mockResolvedValue('### Status\n\n| App | Status |\n|---|---|\n| celery | **suspended** |');

    render(<OpsChatWidget />);
    typeAndSend('**Wie viele Celery-Worker laufen?**');

    // The user turn is intentionally NOT Markdown-rendered — it must show up
    // as plain text, asterisks included.
    expect(await screen.findByText('**Wie viele Celery-Worker laufen?**')).toBeInTheDocument();

    // Exactly one message (the assistant reply) is routed through
    // MarkdownRenderer/react-markdown; the mock renders children verbatim
    // under this testid, proving the raw Markdown reached the renderer
    // instead of being dumped into a plain <Typography>.
    const markdownNodes = await screen.findAllByTestId('react-markdown');
    expect(markdownNodes).toHaveLength(1);
    expect(markdownNodes[0]).toHaveTextContent(
      '### Status | App | Status | |---|---| | celery | **suspended** |'
    );
  });

  it('sends on Enter and inserts a newline instead of sending on Shift+Enter', async () => {
    const sendSpy = jest
      .spyOn(opsChatService, 'sendOpsChatMessage')
      .mockResolvedValue('Antwort.');

    render(<OpsChatWidget />);
    const textbox = screen.getByLabelText('pages.admin.systemHealth.chat.inputLabel');

    fireEvent.change(textbox, { target: { value: 'Shift-Test' } });
    fireEvent.keyDown(textbox, { key: 'Enter', shiftKey: true });
    expect(sendSpy).not.toHaveBeenCalled();

    fireEvent.keyDown(textbox, { key: 'Enter', shiftKey: false });
    expect(await screen.findByText('Antwort.')).toBeInTheDocument();
    expect(sendSpy).toHaveBeenCalledWith('Shift-Test', []);
  });
});
