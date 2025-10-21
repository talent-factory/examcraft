/**
 * QuickActionCard Component Tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QuickActionCard } from '../QuickActionCard';

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('QuickActionCard Component', () => {
  it('renders card with title and description', () => {
    renderWithRouter(
      <QuickActionCard
        icon="📄"
        title="Documents"
        description="Manage your documents"
        path="/documents"
      />
    );

    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Manage your documents')).toBeInTheDocument();
  });

  it('renders icon', () => {
    renderWithRouter(
      <QuickActionCard
        icon="📄"
        title="Documents"
        description="Manage your documents"
        path="/documents"
      />
    );

    expect(screen.getByText('📄')).toBeInTheDocument();
  });

  it('renders link with correct path', () => {
    renderWithRouter(
      <QuickActionCard
        icon="📄"
        title="Documents"
        description="Manage your documents"
        path="/documents"
      />
    );

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/documents');
  });

  it('applies correct color class', () => {
    const { container } = renderWithRouter(
      <QuickActionCard
        icon="📄"
        title="Documents"
        description="Manage your documents"
        path="/documents"
        color="primary"
      />
    );

    const card = container.querySelector('.card');
    expect(card).toHaveClass('bg-primary-50');
  });

  it('renders "Öffnen →" text', () => {
    renderWithRouter(
      <QuickActionCard
        icon="📄"
        title="Documents"
        description="Manage your documents"
        path="/documents"
      />
    );

    expect(screen.getByText('Öffnen →')).toBeInTheDocument();
  });
});

