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
    const { container } = renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    const nav = container.querySelector('nav');
    expect(nav).toBeInTheDocument();
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
    const { container } = renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    // Check for main element
    const main = container.querySelector('main');
    expect(main).toBeInTheDocument();

    // Check for min-h-screen class
    const wrapper = container.querySelector('.min-h-screen');
    expect(wrapper).toBeInTheDocument();
  });

  it('applies correct margin to main content', () => {
    const { container } = renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    const main = container.querySelector('main');
    expect(main).toHaveClass('ml-sidebar');
  });

  it('renders the navigation bar as a fixed element', () => {
    const { container } = renderWithRouter(
      <DashboardLayout>
        <div>Test Content</div>
      </DashboardLayout>
    );

    const nav = container.querySelector('nav');
    expect(nav).not.toBeNull();
    expect(nav).toHaveClass('fixed');
    expect(nav).toHaveClass('top-0');
  });
});
