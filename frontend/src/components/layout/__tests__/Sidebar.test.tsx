/**
 * Sidebar Component Tests
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../Sidebar';
import { AuthProvider } from '../../../contexts/AuthContext';

// Mock apiClient (uses axios ESM which Jest cannot transform)
jest.mock('../../../api/apiClient', () => ({
  setTokenRefreshCallback: jest.fn(),
  setLogoutCallback: jest.fn(),
  setupFetchInterceptor: jest.fn(),
  apiClient: { interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } } },
}));

// Mock useRoleBasedNavigation — overridable per test via mockReturnValue.
const mockUseRoleBasedNavigation = jest.fn();
jest.mock('../../../hooks/useRoleBasedNavigation', () => ({
  useRoleBasedNavigation: () => mockUseRoleBasedNavigation(),
}));

const defaultNavigationItems = [
  { label: 'Dashboard', path: '/dashboard', icon: '📊' },
  { label: 'Documents', path: '/documents', icon: '📄' },
  { label: 'Admin', path: '/admin', icon: '⚙️' },
];

beforeEach(() => {
  mockUseRoleBasedNavigation.mockReturnValue({
    navigationItems: defaultNavigationItems,
  });
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

describe('Sidebar Component', () => {
  it('renders sidebar with navigation items', () => {
    renderWithRouter(<Sidebar isOpen={true} />);

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('renders icons for navigation items', () => {
    renderWithRouter(<Sidebar isOpen={true} />);

    const dashboardLink = screen.getByText('Dashboard').closest('a');
    expect(dashboardLink).toHaveTextContent('📊');
  });

  it('applies active state to current path', () => {
    // Mock window.location.pathname
    Object.defineProperty(window, 'location', {
      value: { pathname: '/dashboard' },
      writable: true,
    });

    renderWithRouter(<Sidebar isOpen={true} />);

    const dashboardLink = screen.getByText('Dashboard').closest('a');
    expect(dashboardLink).toHaveClass('bg-primary-100', 'text-primary-700');
  });

  it('hides labels when sidebar is closed', () => {
    renderWithRouter(<Sidebar isOpen={false} />);

    // Icons should still be visible
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });

  it('renders navigation links with correct href', () => {
    renderWithRouter(<Sidebar isOpen={true} />);

    const dashboardLink = screen.getByText('Dashboard').closest('a');
    expect(dashboardLink).toHaveAttribute('href', '/dashboard');
  });

  describe('flat sibling routes that share a prefix', () => {
    const ACTIVE_CLASS = 'bg-primary-100';

    beforeEach(() => {
      mockUseRoleBasedNavigation.mockReturnValue({
        navigationItems: [
          { label: 'Auswertungen', path: '/auswertungen', icon: '📈' },
          { label: 'Klassen', path: '/auswertungen/klassen', icon: '🎓' },
          { label: 'Studierende', path: '/auswertungen/studierende', icon: '👥' },
        ],
      });
    });

    const renderAt = (pathname: string) =>
      render(
        <MemoryRouter initialEntries={[pathname]}>
          <AuthProvider>
            <Sidebar isOpen={true} />
          </AuthProvider>
        </MemoryRouter>
      );

    it('highlights only the exact match, not the prefix-parent', () => {
      // Regression: at /auswertungen/klassen, the parent /auswertungen
      // would previously also light up because of a startsWith() check
      // without children-awareness.
      renderAt('/auswertungen/klassen');

      expect(screen.getByRole('link', { name: /Klassen/ })).toHaveClass(ACTIVE_CLASS);
      expect(screen.getByRole('link', { name: /Auswertungen/ })).not.toHaveClass(
        ACTIVE_CLASS,
      );
    });

    it('highlights the parent at its own exact path', () => {
      renderAt('/auswertungen');

      expect(screen.getByRole('link', { name: /Auswertungen/ })).toHaveClass(
        ACTIVE_CLASS,
      );
      expect(screen.getByRole('link', { name: /Klassen/ })).not.toHaveClass(
        ACTIVE_CLASS,
      );
    });
  });

  describe('items with children', () => {
    const ACTIVE_CLASS = 'bg-primary-100';

    beforeEach(() => {
      mockUseRoleBasedNavigation.mockReturnValue({
        navigationItems: [
          {
            label: 'Reports',
            path: '/reports',
            icon: '📊',
            children: [{ label: 'Daily', path: '/reports/daily', icon: '📅' }],
          },
        ],
      });
    });

    it('keeps the parent active when a descendant route is open', () => {
      // Items with real children intentionally use prefix matching so
      // that the parent stays highlighted while a sub-route is shown.
      render(
        <MemoryRouter initialEntries={['/reports/daily']}>
          <AuthProvider>
            <Sidebar isOpen={true} />
          </AuthProvider>
        </MemoryRouter>
      );

      expect(screen.getByRole('link', { name: /Reports/ })).toHaveClass(ACTIVE_CLASS);
    });
  });
});
