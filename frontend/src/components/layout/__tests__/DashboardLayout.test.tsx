/**
 * DashboardLayout Component Tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
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
// Mock Sidebar
jest.mock('../Sidebar', () => ({
  Sidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));

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
});
