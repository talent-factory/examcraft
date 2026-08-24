import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
// jest.mock calls are hoisted above the imports by babel-jest, so the import
// of HelpWidgetGate below already sees the mocks defined further down.
import HelpWidgetGate from '../HelpWidgetGate';

const mockUseAuth = jest.fn();

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// HelpWidget is stubbed: the gate test should only check whether it mounts —
// not pull in the whole widget tree (incl. useHelpContext and its requests).
const mockHelpWidgetRender = jest.fn();
jest.mock('../HelpWidget', () => ({
  __esModule: true,
  default: () => {
    mockHelpWidgetRender();
    return <div data-testid="help-widget" />;
  },
}));

describe('HelpWidgetGate', () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
    mockHelpWidgetRender.mockClear();
  });

  it('rendert null wenn nicht authentifiziert', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });

    const { container } = render(<HelpWidgetGate />);

    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByTestId('help-widget')).not.toBeInTheDocument();
    expect(mockHelpWidgetRender).not.toHaveBeenCalled();
  });

  it('rendert null während des Token-Bootstraps (isLoading)', () => {
    // No FAB flash before the first auth result: isAuthenticated is still
    // false here, but may flip to true right afterwards.
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: true });

    const { container } = render(<HelpWidgetGate />);

    expect(container).toBeEmptyDOMElement();
    expect(mockHelpWidgetRender).not.toHaveBeenCalled();
  });

  it('rendert null bei isLoading auch wenn bereits authentifiziert', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: true });

    const { container } = render(<HelpWidgetGate />);

    expect(container).toBeEmptyDOMElement();
    expect(mockHelpWidgetRender).not.toHaveBeenCalled();
  });

  it('rendert HelpWidget wenn authentifiziert und fertig geladen', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });

    render(<HelpWidgetGate />);

    expect(screen.getByTestId('help-widget')).toBeInTheDocument();
    expect(mockHelpWidgetRender).toHaveBeenCalled();
  });

  it('entfernt das Widget beim Logout', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });
    const { rerender } = render(<HelpWidgetGate />);
    expect(screen.getByTestId('help-widget')).toBeInTheDocument();

    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });
    rerender(<HelpWidgetGate />);

    expect(screen.queryByTestId('help-widget')).not.toBeInTheDocument();
  });
});
