/**
 * DashboardLayout Component Tests
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { DashboardLayout } from '../DashboardLayout';
import { AuthProvider } from '../../../contexts/AuthContext';

// Mock apiClient (uses axios ESM which Jest cannot transform)
jest.mock('../../../api/apiClient', () => ({
  setTokenRefreshCallback: jest.fn(),
  setLogoutCallback: jest.fn(),
  setAdoptStoredTokensCallback: jest.fn(),
  setupFetchInterceptor: jest.fn(),
  apiClient: { interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } },
}));

// NavigationBar deliberately not mocked: the real <nav> must render so the fixed/top-0 test can check it
// Mock Sidebar — exposes isOpen/onToggle so the collapse-persistence tests
// below can drive DashboardLayout's real state without rendering the full
// Sidebar tree.
jest.mock('../Sidebar', () => ({
  Sidebar: ({ isOpen, onToggle }: { isOpen?: boolean; onToggle?: (isOpen: boolean) => void }) => (
    <div data-testid="sidebar">
      Sidebar
      {onToggle && (
        <button type="button" data-testid="mock-sidebar-toggle" onClick={() => onToggle(!isOpen)}>
          toggle
        </button>
      )}
    </div>
  ),
}));

beforeEach(() => {
  window.localStorage.clear();
});

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        {component}
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('DashboardLayout Component', () => {
  it('renders navigation bar', () => {
    renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    expect(screen.getByTestId('navigation-bar')).toBeInTheDocument();
  });

  it('renders sidebar', () => {
    renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('renders children content', () => {
    renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('has correct layout structure', () => {
    renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    // Check for main element
    expect(screen.getByRole('main')).toBeInTheDocument();

    // Check for dashboard layout wrapper
    expect(screen.getByTestId('dashboard-layout')).toBeInTheDocument();
  });

  it('applies correct margin to main content', () => {
    renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    expect(screen.getByRole('main')).toHaveClass('ml-sidebar');
  });

  it('renders footer with legal links', () => {
    renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    expect(screen.getByTestId('app-footer')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Datenschutzerklärung/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Nutzungsbedingungen/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Impressum/i })).toBeInTheDocument();
  });

  it('renders the navigation bar as a fixed element', () => {
    renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    const nav = screen.getByTestId('navigation-bar');
    expect(nav).toHaveClass('fixed');
    expect(nav).toHaveClass('top-0');
  });

  describe('sidebar collapse persistence (TF-819)', () => {
    it('restores a collapsed state from localStorage instead of always starting open', () => {
      window.localStorage.setItem('examcraft.sidebar.isOpen', 'false');

      renderWithRouter(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>
      );

      expect(screen.getByRole('main')).toHaveClass('ml-sidebar-collapsed');
    });

    it('persists a collapse toggle and survives a remount at a different route depth', () => {
      // Regression: some routes wrap DashboardLayout at a different component
      // depth (e.g. behind an extra guard), which unmounts/remounts it on
      // navigation. Before TF-819's fix, a plain useState(true) would reset
      // to expanded on every such remount, undoing the user's toggle.
      const { unmount } = renderWithRouter(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>
      );

      expect(screen.getByRole('main')).toHaveClass('ml-sidebar');
      fireEvent.click(screen.getByTestId('mock-sidebar-toggle'));
      expect(screen.getByRole('main')).toHaveClass('ml-sidebar-collapsed');

      unmount();

      renderWithRouter(
        <DashboardLayout>
          <div>Test Content</div>
        </DashboardLayout>
      );

      expect(screen.getByRole('main')).toHaveClass('ml-sidebar-collapsed');
    });
  });
});
