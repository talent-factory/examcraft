/**
 * CompliancePage Tests (TF-746)
 *
 * The page fetches its content from GET /api/v1/legal/compliance —
 * unlike the static Privacy/Terms/Imprint pages — so these tests mock
 * `fetch` rather than exercising a live backend.
 *
 * This file overrides the global `react-i18next` mock from
 * `setupTests.ts` (which hardcodes `i18n.language: 'de'`) so it can
 * exercise the German-only-notice banner, which depends on the current
 * UI language. `mockLanguage` is intentionally prefixed with "mock" —
 * Jest's module-factory hoisting only allows referencing out-of-scope
 * variables whose name matches that prefix.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { CompliancePage } from '../CompliancePage';

let mockLanguage = 'de';

jest.mock('react-i18next', () => {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const mockTranslations = require('../../../locales/de/translation.json');

  function mockResolveKey(obj: Record<string, unknown>, key: string): unknown {
    const parts = key.split('.');
    let current: unknown = obj;
    for (const part of parts) {
      if (current == null || typeof current !== 'object') return key;
      current = (current as Record<string, unknown>)[part];
    }
    return current;
  }

  return {
    useTranslation: () => ({
      t: (key: string) => {
        const value = mockResolveKey(mockTranslations, key);
        return typeof value === 'string' ? value : key;
      },
      i18n: { language: mockLanguage, changeLanguage: jest.fn() },
    }),
    initReactI18next: { type: '3rdParty', init: jest.fn() },
  };
});

const STUB_RESPONSE = {
  avv: {
    title: 'Muster — Auftragsverarbeitungsvertrag (AVV) nach Art. 28 DSGVO',
    last_updated: 'Stand: August 2026',
    draft_notice: 'ENTWURF – juristische Prüfung ausstehend.',
    sections: [{ heading: '1. Gegenstand und Dauer', paragraphs: ['Text A'] }],
  },
  tom: {
    title: 'Anlage — Technische und organisatorische Massnahmen (TOM)',
    last_updated: 'Stand: August 2026',
    draft_notice: 'ENTWURF – juristische Prüfung ausstehend.',
    sections: [{ heading: '1. Vertraulichkeit', paragraphs: ['Text B'] }],
  },
  subprocessors: [
    {
      name: 'Anthropic PBC',
      purpose: 'KI-gestützte Fragengenerierung',
      location: 'USA',
      transfer_mechanism: 'SCC',
      change_notice: '30 Tage Vorlauf',
    },
  ],
  vvt_text: 'Verzeichnis von Verarbeitungstätigkeiten — Textbaustein für ExamCraft',
  state_specific_notes: {
    heading: 'Landesspezifika — Prüfhinweis für Legal',
    paragraphs: ['Baden-Württemberg: § 115b SchulG.'],
  },
};

const renderWithRouter = (ui: React.ReactElement) =>
  render(<BrowserRouter>{ui}</BrowserRouter>);

describe('CompliancePage', () => {
  beforeEach(() => {
    mockLanguage = 'de';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(STUB_RESPONSE),
    }) as jest.Mock;
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('renders the page heading and both PDF download links once loaded', async () => {
    renderWithRouter(<CompliancePage />);

    expect(
      await screen.findByRole('heading', { name: /AVV, TOM & Compliance-Dokumente/i }),
    ).toBeInTheDocument();

    const avvLink = await screen.findByRole('link', { name: /AVV als PDF herunterladen/i });
    expect(avvLink).toHaveAttribute('href', expect.stringContaining('/api/v1/legal/avv.pdf'));

    const tomLink = await screen.findByRole('link', {
      name: /TOM-Anlage als PDF herunterladen/i,
    });
    expect(tomLink).toHaveAttribute('href', expect.stringContaining('/api/v1/legal/tom.pdf'));
  });

  it('renders the AVV and TOM section text fetched from the backend', async () => {
    renderWithRouter(<CompliancePage />);

    expect(await screen.findByText('1. Gegenstand und Dauer')).toBeInTheDocument();
    expect(screen.getByText('Text A')).toBeInTheDocument();
    expect(screen.getByText('1. Vertraulichkeit')).toBeInTheDocument();
    expect(screen.getByText('Text B')).toBeInTheDocument();
  });

  it('renders the subprocessor table with every service from the response', async () => {
    renderWithRouter(<CompliancePage />);

    expect(await screen.findByRole('table')).toBeInTheDocument();
    expect(screen.getByText('Anthropic PBC')).toBeInTheDocument();
    expect(screen.getByText('30 Tage Vorlauf')).toBeInTheDocument();
  });

  it('renders the VVT text block with a copy-to-clipboard button', async () => {
    renderWithRouter(<CompliancePage />);

    expect(await screen.findByText(/Textbaustein für ExamCraft/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /In Zwischenablage kopieren/i }),
    ).toBeInTheDocument();
  });

  it('copies the VVT text to the clipboard and shows a confirmation', async () => {
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    renderWithRouter(<CompliancePage />);
    const button = await screen.findByRole('button', { name: /In Zwischenablage kopieren/i });

    fireEvent.click(button);

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(STUB_RESPONSE.vvt_text);
    });
    expect(await screen.findByRole('button', { name: /Kopiert!/i })).toBeInTheDocument();
  });

  it('falls back to a manual-copy hint when the clipboard write fails, without crashing', async () => {
    const writeText = jest.fn().mockRejectedValue(new Error('NotAllowedError'));
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    renderWithRouter(<CompliancePage />);
    const button = await screen.findByRole('button', { name: /In Zwischenablage kopieren/i });

    fireEvent.click(button);

    expect(
      await screen.findByText(/Automatisches Kopieren nicht möglich/i),
    ).toBeInTheDocument();
    // The button itself must stay intact and clickable — a crash here
    // would have already failed the `findByText` above via an error
    // boundary, but assert the button is still there for clarity.
    expect(screen.getByRole('button', { name: /In Zwischenablage kopieren/i })).toBeInTheDocument();
  });

  it('renders the state-specific notes section', async () => {
    renderWithRouter(<CompliancePage />);

    expect(await screen.findByText(/§ 115b SchulG/i)).toBeInTheDocument();
  });

  it('shows a loading indicator before the content resolves', async () => {
    let resolveFetch: (value: unknown) => void = () => {};
    global.fetch = jest.fn().mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    ) as jest.Mock;

    renderWithRouter(<CompliancePage />);

    expect(await screen.findByText(/Dokumente werden geladen/i)).toBeInTheDocument();

    resolveFetch({ ok: true, json: () => Promise.resolve(STUB_RESPONSE) });

    await waitFor(() => {
      expect(screen.queryByText(/Dokumente werden geladen/i)).not.toBeInTheDocument();
    });
    expect(
      await screen.findByRole('heading', { name: /AVV, TOM & Compliance-Dokumente/i }),
    ).toBeInTheDocument();
  });

  it('shows an error message with a retry button when the compliance content fails to load', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500 }) as jest.Mock;

    renderWithRouter(<CompliancePage />);

    expect(
      await screen.findByText(/Die Compliance-Dokumente konnten nicht geladen werden/i),
    ).toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: /Erneut versuchen/i });
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(STUB_RESPONSE),
    }) as jest.Mock;

    fireEvent.click(retryButton);

    expect(
      await screen.findByRole('heading', { name: /AVV, TOM & Compliance-Dokumente/i }),
    ).toBeInTheDocument();
  });

  it('shows the German-only notice when the UI language is not German', async () => {
    mockLanguage = 'fr';

    renderWithRouter(<CompliancePage />);

    expect(
      await screen.findByText(/liegen ausschliesslich auf Deutsch vor/i),
    ).toBeInTheDocument();
  });

  it('hides the German-only notice for regional German locale codes like de-CH', async () => {
    // Regression test: `i18n.language !== 'de'` used to compare the raw
    // BCP-47 tag, which never equals 'de' for regional codes such as
    // 'de-CH' — the fix compares only the first two characters.
    mockLanguage = 'de-CH';

    renderWithRouter(<CompliancePage />);

    await screen.findByRole('heading', { name: /AVV, TOM & Compliance-Dokumente/i });
    expect(
      screen.queryByText(/liegen ausschliesslich auf Deutsch vor/i),
    ).not.toBeInTheDocument();
  });
});
