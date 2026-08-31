/**
 * ImpersonationBanner tests (TF-743).
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ImpersonationBanner } from '../ImpersonationBanner';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// The backend end-call now lives inside AuthContext's endImpersonation()
// (restoreAdminSession), not in this component — see AuthContext.test.tsx
// for coverage of that call and its best-effort failure handling. Here we
// only need to mock the context's endImpersonation() result.
const mockEndImpersonation = jest.fn();
let mockAuthState: {
  isImpersonating: boolean;
  impersonationExpiresAt: string | null;
  user: { first_name: string; last_name: string; email: string } | null;
};

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ ...mockAuthState, endImpersonation: mockEndImpersonation }),
}));

beforeEach(() => {
  jest.clearAllMocks();
  mockAuthState = {
    isImpersonating: false,
    impersonationExpiresAt: null,
    user: null,
  };
  mockEndImpersonation.mockResolvedValue({ backendEndFailed: false });
});

describe('ImpersonationBanner', () => {
  it('renders nothing when not impersonating', () => {
    const { container } = render(<ImpersonationBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the target user and a countdown to the effective fallback deadline while impersonating', () => {
    // Session hard-caps at 5 min, but the proactive timer (REFRESH_LEAD_MS)
    // falls back to the admin 2 min before that — the countdown must reflect
    // the real ~3 min remaining, not the full 5.
    mockAuthState = {
      isImpersonating: true,
      impersonationExpiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
      user: { first_name: 'Max', last_name: 'Muster', email: 'max@example.com' },
    };

    render(<ImpersonationBanner />);

    expect(screen.getByTestId('impersonation-banner')).toBeInTheDocument();
    expect(screen.getByText(/Max Muster/)).toBeInTheDocument();
    expect(screen.getByText(/max@example\.com/)).toBeInTheDocument();
    // Exact-substring assertions here are inherently flaky at second
    // boundaries; accept the one-second window around the real deadline.
    expect(screen.getByTestId('impersonation-banner-countdown')).toHaveTextContent(/(2:59|3:00)$/);
  });

  it('ends impersonation and navigates to the dashboard on "back to my account"', async () => {
    mockAuthState = {
      isImpersonating: true,
      impersonationExpiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
      user: { first_name: 'Max', last_name: 'Muster', email: 'max@example.com' },
    };

    render(<ImpersonationBanner />);

    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/dashboard'));
    expect(mockEndImpersonation).toHaveBeenCalled();
    expect(screen.queryByTestId('impersonation-banner-server-end-failed')).not.toBeInTheDocument();
  });

  it('still navigates, but surfaces a notice, when the server-side end call failed (endImpersonation reports backendEndFailed)', async () => {
    mockAuthState = {
      isImpersonating: true,
      impersonationExpiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
      user: { first_name: 'Max', last_name: 'Muster', email: 'max@example.com' },
    };
    // The real endImpersonation() always restores locally (isImpersonating
    // flips to false) regardless of whether the backend call succeeded;
    // mirror that side effect here since useAuth is mocked.
    mockEndImpersonation.mockImplementation(async () => {
      mockAuthState = { isImpersonating: false, impersonationExpiresAt: null, user: null };
      return { backendEndFailed: true };
    });

    render(<ImpersonationBanner />);

    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/dashboard'));
    expect(mockEndImpersonation).toHaveBeenCalled();

    // The local restore (and navigation) happens regardless — this notice
    // is purely informational, not a blocker. It must stay visible after
    // navigate() since a support engineer chasing a stuck impersonation
    // session needs a starting point beyond a browser console nobody was
    // watching.
    await waitFor(() => {
      expect(screen.getByTestId('impersonation-banner-server-end-failed')).toBeInTheDocument();
    });
  });
});
