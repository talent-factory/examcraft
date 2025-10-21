/**
 * DashboardLayout Component Tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { DashboardLayout } from '../DashboardLayout';
import { AuthProvider } from '../../../contexts/AuthContext';

// Mock NavigationBar
jest.mock('../NavigationBar', () => ({
  NavigationBar: () => <div data-testid="navigation-bar">Navigation Bar</div>,
}));

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
});

