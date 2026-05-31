/**
 * Tests für DocumentOcrQualityBadges (TF-361).
 *
 * react-i18next ist lokal gemockt (t gibt den Key zurück), damit die Assertions
 * unabhängig von Übersetzungsinhalten auf stabilen data-testid-Markern fussen.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentOcrQualityBadges from '../DocumentOcrQualityBadges';
import {
  Document,
  DocumentQuality,
  DocumentStatus,
} from '../../../types/document';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) =>
      typeof fallback === 'string' ? fallback : key,
    i18n: { language: 'de' },
  }),
}));

const theme = createTheme();
const wrap = (ui: React.ReactElement) => (
  <ThemeProvider theme={theme}>{ui}</ThemeProvider>
);

const makeDoc = (overrides: Partial<Document> = {}): Document => ({
  id: 1,
  filename: 'doc.docx',
  original_filename: 'doc.docx',
  title: 'Doc',
  mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  status: DocumentStatus.PROCESSED,
  created_at: '2026-05-29T00:00:00Z',
  has_vectors: true,
  ...overrides,
});

const okQuality: DocumentQuality = { ok: true, reason: 'ok' };
const badQuality = (reason: string): DocumentQuality => ({ ok: false, reason });

describe('DocumentOcrQualityBadges', () => {
  it('zeigt den OCR-Badge, wenn processed_with_ocr true ist', () => {
    render(
      wrap(
        <DocumentOcrQualityBadges
          document={makeDoc({ processed_with_ocr: true, quality: okQuality })}
        />,
      ),
    );
    expect(screen.getByTestId('ocr-badge')).toBeInTheDocument();
    expect(screen.queryByTestId('quality-warning-badge')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ocr-reprocessing-badge')).not.toBeInTheDocument();
  });

  it('zeigt den Qualitäts-Warnchip bei quality.ok === false', () => {
    render(
      wrap(
        <DocumentOcrQualityBadges
          document={makeDoc({ quality: badQuality('scanned_low_text') })}
        />,
      ),
    );
    expect(screen.getByTestId('quality-warning-badge')).toBeInTheDocument();
    expect(screen.queryByTestId('ocr-badge')).not.toBeInTheDocument();
  });

  it('zeigt während der OCR-Neuverarbeitung nur den Reprocessing-Hinweis', () => {
    render(
      wrap(
        <DocumentOcrQualityBadges
          document={makeDoc({
            status: DocumentStatus.PROCESSING,
            quality: badQuality('scanned_low_text'),
            processed_with_ocr: false,
          })}
        />,
      ),
    );
    expect(screen.getByTestId('ocr-reprocessing-badge')).toBeInTheDocument();
    // Kein widersprüchlicher Qualitäts-/OCR-Badge während des Reprocess.
    expect(screen.queryByTestId('quality-warning-badge')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ocr-badge')).not.toBeInTheDocument();
  });

  it('zeigt OCR-Badge UND Warnchip, wenn OCR lief aber Qualität weiter ungenügend ist', () => {
    render(
      wrap(
        <DocumentOcrQualityBadges
          document={makeDoc({
            status: DocumentStatus.PROCESSED,
            processed_with_ocr: true,
            quality: badQuality('garbage_extraction'),
          })}
        />,
      ),
    );
    expect(screen.getByTestId('ocr-badge')).toBeInTheDocument();
    expect(screen.getByTestId('quality-warning-badge')).toBeInTheDocument();
  });

  it('zeigt den Reprocessing-Hinweis bei escalation "queued", auch wenn der Status noch PROCESSED ist (TF-365 Fenster A)', () => {
    // Zwischen Einreihen der Eskalation und Start des Reprocess-Jobs steht das
    // Dokument noch auf PROCESSED — ohne escalation würde nur ein grüner Status
    // ohne Reprocess-Hinweis erscheinen.
    render(
      wrap(
        <DocumentOcrQualityBadges
          document={makeDoc({
            status: DocumentStatus.PROCESSED,
            quality: badQuality('scanned_low_text'),
            processed_with_ocr: false,
            escalation: 'queued',
          })}
        />,
      ),
    );
    expect(screen.getByTestId('ocr-reprocessing-badge')).toBeInTheDocument();
    expect(screen.queryByTestId('quality-warning-badge')).not.toBeInTheDocument();
  });

  it('zeigt einen Fehlschlag-Hinweis bei escalation "failed" (TF-365 PROCESSED→ERROR nachvollziehbar)', () => {
    render(
      wrap(
        <DocumentOcrQualityBadges
          document={makeDoc({
            status: DocumentStatus.ERROR,
            quality: badQuality('scanned_low_text'),
            processed_with_ocr: false,
            escalation: 'failed',
          })}
        />,
      ),
    );
    expect(screen.getByTestId('ocr-failed-badge')).toBeInTheDocument();
    // Early-Return: kein widersprüchlicher Qualitäts-/OCR-Chip neben dem Fehler.
    expect(screen.queryByTestId('quality-warning-badge')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ocr-badge')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ocr-reprocessing-badge')).not.toBeInTheDocument();
  });

  it('zeigt bei escalation "exhausted" die bestehenden OCR-+Qualitäts-Badges (kein Reprocessing/Fehler)', () => {
    // OCR lief, Qualität weiter ungenügend: keine weitere Eskalation, daher kein
    // Reprocessing-Hinweis und kein Fehler-Chip — nur OCR-Badge + Qualitätswarnung.
    render(
      wrap(
        <DocumentOcrQualityBadges
          document={makeDoc({
            status: DocumentStatus.PROCESSED,
            processed_with_ocr: true,
            quality: badQuality('garbage_extraction'),
            escalation: 'exhausted',
          })}
        />,
      ),
    );
    expect(screen.getByTestId('ocr-badge')).toBeInTheDocument();
    expect(screen.getByTestId('quality-warning-badge')).toBeInTheDocument();
    expect(screen.queryByTestId('ocr-reprocessing-badge')).not.toBeInTheDocument();
    expect(screen.queryByTestId('ocr-failed-badge')).not.toBeInTheDocument();
  });

  it('rendert nichts, wenn weder OCR noch ein negatives Verdict vorliegt', () => {
    const { container } = render(
      wrap(<DocumentOcrQualityBadges document={makeDoc({ quality: okQuality })} />),
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('rendert nichts, wenn quality null und kein OCR', () => {
    const { container } = render(
      wrap(<DocumentOcrQualityBadges document={makeDoc({ quality: null })} />),
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('zeigt bei reason "ocr_pages_discarded" den Warnchip mit der Seitenanzahl', () => {
    render(
      wrap(
        <DocumentOcrQualityBadges
          document={makeDoc({
            status: DocumentStatus.PROCESSED,
            processed_with_ocr: true,
            quality: {
              ok: false,
              reason: 'ocr_pages_discarded',
              signals: { ocr_pages_discarded: 3, ocr_pages_attempted: 8 },
            },
          })}
        />,
      ),
    );
    const badge = screen.getByTestId('quality-warning-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute('data-ocr-discarded', '3');
  });
});
