/**
 * Legal Pages Tests
 *
 * Smoke tests for Privacy, Terms and Imprint pages.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { PrivacyPage, TermsPage, ImprintPage } from '../';

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('Legal pages', () => {
  it('renders the privacy policy page', () => {
    renderWithRouter(<PrivacyPage />);
    expect(screen.getByRole('heading', { name: /Datenschutzerklärung/i })).toBeInTheDocument();
    expect(screen.getByText(/Talent Factory GmbH/i)).toBeInTheDocument();
  });

  it('renders the terms of service page', () => {
    renderWithRouter(<TermsPage />);
    expect(screen.getByRole('heading', { name: /Nutzungsbedingungen/i })).toBeInTheDocument();
  });

  it('renders the imprint page', () => {
    renderWithRouter(<ImprintPage />);
    expect(screen.getByRole('heading', { name: /Impressum/i })).toBeInTheDocument();
  });

  it('renders navigation between legal pages', () => {
    renderWithRouter(<PrivacyPage />);
    expect(screen.getByRole('link', { name: /Nutzungsbedingungen/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Impressum/i })).toBeInTheDocument();
  });
});
