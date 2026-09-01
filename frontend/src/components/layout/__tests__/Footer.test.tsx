/**
 * Footer Component Tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Footer } from '../Footer';

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('Footer Component', () => {
  it('renders the footer', () => {
    renderWithRouter(<Footer />);
    expect(screen.getByTestId('app-footer')).toBeInTheDocument();
  });

  it('renders links to legal pages', () => {
    renderWithRouter(<Footer />);
    expect(screen.getByRole('link', { name: /Datenschutzerklärung/i })).toHaveAttribute('href', '/privacy');
    expect(screen.getByRole('link', { name: /Nutzungsbedingungen/i })).toHaveAttribute('href', '/terms');
    expect(screen.getByRole('link', { name: /Impressum/i })).toHaveAttribute('href', '/imprint');
  });

  it('renders the copyright notice', () => {
    renderWithRouter(<Footer />);
    expect(screen.getByText(/ExamCraft AI/i)).toBeInTheDocument();
  });

  it('renders the AI/privacy notice with a deep link to the AI section of the Privacy Page', () => {
    renderWithRouter(<Footer />);
    const notice = screen.getByTestId('footer-ai-notice');
    expect(notice).toHaveTextContent(/KI-Modelle/i);
    const aiNoticeLink = screen.getByRole('link', { name: /Mehr erfahren/i });
    expect(aiNoticeLink).toHaveAttribute('href', '/privacy#ai-data-flows');
    // The accessible name (from aria-label) must still start with the visible
    // link text ("Mehr erfahren") per WCAG 2.5.3 Label in Name.
    expect(aiNoticeLink.textContent).toBe('Mehr erfahren');
  });
});
