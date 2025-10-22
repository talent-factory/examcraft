/**
 * Sidebar Component Tests
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Sidebar } from '../Sidebar';
import { AuthProvider } from '../../../contexts/AuthContext';

// Mock useRoleBasedNavigation
jest.mock('../../../hooks/useRoleBasedNavigation', () => ({
  useRoleBasedNavigation: () => ({
    navigationItems: [
      {
        label: 'Dashboard',
        path: '/dashboard',
        icon: '📊',
      },
      {
        label: 'Documents',
        path: '/documents',
        icon: '📄',
      },
      {
        label: 'Admin',
        path: '/admin',
        icon: '⚙️',
        children: [
          {
            label: 'Users',
            path: '/admin/users',
            icon: '👥',
          },
        ],
      },
    ],
  }),
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

  it('expands and collapses submenu items', () => {
    renderWithRouter(<Sidebar isOpen={true} />);
    
    // Initially, submenu should not be visible
    expect(screen.queryByText('Users')).not.toBeInTheDocument();
    
    // Click expand button
    const expandButton = screen.getByRole('button', { name: /expand/i });
    fireEvent.click(expandButton);
    
    // Submenu should now be visible
    expect(screen.getByText('Users')).toBeInTheDocument();
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
});

