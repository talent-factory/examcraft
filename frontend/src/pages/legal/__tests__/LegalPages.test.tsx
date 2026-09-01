/**
 * Legal Pages Tests
 *
 * Smoke tests for Privacy, Terms and Imprint pages.
 */

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import i18n from '../../../i18n'; // load the real i18n instance
import { PrivacyPage, TermsPage, ImprintPage } from '../';

// setupTests.ts installs a global mock for 'react-i18next' that always
// resolves keys against the German translation file, regardless of the
// requested language. The `legal.privacy.ai.functions` key is consumed via
// `t(..., { returnObjects: true })` and cast to an array in PrivacyPage.tsx
// (TF-766) — if any shipped locale's translation JSON ever lost or
// malformed that key, the resulting `.map()` call would throw at render
// time (a full-page crash for whichever language hit it, not just wrong
// copy), and the global mock cannot catch that. We unmock react-i18next
// here and drive the real i18n instance against the actual en/fr/it
// resources too (same pattern as ProfileView.test.tsx). jest.mock/unmock
// calls are hoisted above all imports by babel-plugin-jest-hoist, so this
// takes effect before the imports above (which transitively require
// 'react-i18next') are resolved.
jest.unmock('react-i18next');

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('Legal pages', () => {
  // jsdom's navigator.language ('en-US') would otherwise make
  // i18next-browser-languagedetector pick 'en' instead of 'de', so force
  // the language explicitly for deterministic assertions.
  beforeAll(async () => {
    await i18n.changeLanguage('de');
  });

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

  describe('LLM data flow section (TF-766)', () => {
    it('renders the section heading, all four function entries, and the surrounding explanatory text', () => {
      renderWithRouter(<PrivacyPage />);
      expect(
        screen.getByRole('heading', { name: /Übermittlung von Inhalten an KI-Modelle/i })
      ).toBeInTheDocument();
      expect(screen.getByText(/Human-in-the-Loop-Prinzip/i)).toBeInTheDocument();
      expect(
        screen.getByText(/nutzt KI-Modelle über ein zentrales LLM-Gateway/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/Fragengenerierung:/i)).toBeInTheDocument();
      expect(screen.getByText(/Hilfe-Chat:/i)).toBeInTheDocument();
      expect(screen.getByText(/Automatische Bewertung:/i)).toBeInTheDocument();
      expect(screen.getByText(/Dokumentenindexierung:/i)).toBeInTheDocument();
      expect(screen.getByText(/dokumentengestützte Chat-Assistent/i)).toBeInTheDocument();
      expect(screen.getByText(/Nicht übermittelt werden:/i)).toBeInTheDocument();
      expect(screen.getByText(/Ob die Daten die EU verlassen/i)).toBeInTheDocument();
    });

    it('exposes exactly the documented AI functions as the section list, no more and no fewer', () => {
      renderWithRouter(<PrivacyPage />);
      const section = screen.getByTestId('ai-data-flows-section');
      const items = within(section).getAllByRole('listitem');
      expect(items).toHaveLength(4);
    });

    it('anchors the section as #ai-data-flows so the footer deep link resolves to it', () => {
      renderWithRouter(<PrivacyPage />);
      const section = screen.getByTestId('ai-data-flows-section');
      expect(section).toHaveAttribute('id', 'ai-data-flows');
      expect(
        within(section).getByRole('heading', {
          name: /Übermittlung von Inhalten an KI-Modelle/i,
        })
      ).toBeInTheDocument();
    });
  });

  describe('Privacy page AI section renders safely in every shipped locale', () => {
    afterEach(async () => {
      // Reset to the suite default so a later test in this file doesn't
      // inherit a non-German locale.
      await i18n.changeLanguage('de');
    });

    it.each(['de', 'en', 'fr', 'it'])(
      'locale "%s" renders the AI section without throwing',
      async (locale) => {
        await i18n.changeLanguage(locale);
        expect(() => renderWithRouter(<PrivacyPage />)).not.toThrow();
        const section = screen.getByTestId('ai-data-flows-section');
        const items = within(section).getAllByRole('listitem');
        expect(items.length).toBeGreaterThan(0);
        items.forEach((item) => {
          expect(item.textContent?.trim().length).toBeGreaterThan(0);
        });
      }
    );
  });
});
