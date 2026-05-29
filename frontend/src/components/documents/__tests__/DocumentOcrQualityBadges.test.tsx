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
});
