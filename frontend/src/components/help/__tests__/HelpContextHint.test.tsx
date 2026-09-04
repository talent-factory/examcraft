import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import HelpContextHint from '../HelpContextHint';
import { helpService } from '../../../services/HelpService';

jest.mock('../../../services/HelpService', () => ({
  helpService: {
    dismissHint: jest.fn(),
  },
}));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ accessToken: 'test-token' }),
}));

const mockedDismissHint = helpService.dismissHint as jest.Mock;

const hint = { i18n_key: 'help.hints.examsCompose', hint_id: 6 };

const renderHint = (overrides: Partial<typeof hint> = {}) =>
  render(
    <HelpContextHint
      hint={{ ...hint, ...overrides }}
      onDismiss={jest.fn()}
      onDismissPermanently={jest.fn()}
    />
  );

describe('HelpContextHint — collapse/expand toggle', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('is collapsed by default (aria-expanded=false)', () => {
    renderHint();
    expect(screen.getByTestId('help-context-hint-toggle')).toHaveAttribute(
      'aria-expanded',
      'false'
    );
  });

  it('expands on click and collapses again on a second click', () => {
    renderHint();
    const toggle = screen.getByTestId('help-context-hint-toggle');

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('expands on Enter and on Space', () => {
    renderHint();
    const toggle = screen.getByTestId('help-context-hint-toggle');

    fireEvent.keyDown(toggle, { key: 'Enter' });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');

    fireEvent.keyDown(toggle, { key: ' ' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('has no interactive descendant inside the role="button" toggle row', () => {
    // Regression guard: the chevron used to be a real MUI IconButton nested
    // inside this same role="button" row — invalid ARIA (an interactive
    // element inside a button), a second, functionally-dead tab stop, and a
    // static aria-label that couldn't reflect `expanded`. Now it's a plain
    // aria-hidden Box: the row itself is the only interactive thing here.
    renderHint();
    const toggle = screen.getByTestId('help-context-hint-toggle');
    expect(within(toggle).queryByRole('button')).not.toBeInTheDocument();
    expect(within(toggle).queryAllByRole('button', { hidden: true })).toHaveLength(0);
  });
});

describe('HelpContextHint — permanent dismissal', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    (console.warn as jest.Mock).mockRestore();
  });

  it('calls onDismissPermanently after a successful server dismiss', async () => {
    mockedDismissHint.mockResolvedValueOnce(undefined);
    const onDismissPermanently = jest.fn();

    render(
      <HelpContextHint
        hint={hint}
        onDismiss={jest.fn()}
        onDismissPermanently={onDismissPermanently}
      />
    );

    fireEvent.click(screen.getByTestId('help-context-hint-toggle'));
    fireEvent.click(screen.getByText('Nicht mehr anzeigen'));

    // Both assertions need waitFor: dismissHint is recorded synchronously on
    // call, but onDismissPermanently only runs after that promise resolves —
    // asserting it right after the first waitFor would race the microtask.
    await waitFor(() => expect(mockedDismissHint).toHaveBeenCalledWith('test-token', 6));
    await waitFor(() => expect(onDismissPermanently).toHaveBeenCalled());
  });

  it('leaves the hint displayed and logs a warning when the server dismiss fails', async () => {
    // TF-625 review finding: this used to have no try/catch at all — a
    // failure vanished with no trace and onDismissPermanently ran anyway.
    mockedDismissHint.mockRejectedValueOnce(new Error('network error'));
    const onDismissPermanently = jest.fn();

    render(
      <HelpContextHint
        hint={hint}
        onDismiss={jest.fn()}
        onDismissPermanently={onDismissPermanently}
      />
    );

    fireEvent.click(screen.getByTestId('help-context-hint-toggle'));
    fireEvent.click(screen.getByText('Nicht mehr anzeigen'));

    await waitFor(() =>
      expect(console.warn).toHaveBeenCalledWith(
        expect.stringContaining('Failed to permanently dismiss hint'),
        expect.any(Error)
      )
    );
    expect(onDismissPermanently).not.toHaveBeenCalled();
  });
});
