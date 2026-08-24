/**
 * DocumentOcrQualityBadges — OCR/quality status badges (TF-361).
 *
 * Follow-up ticket to the backend OCR escalation (TF-360). Based on the
 * backend-exposed fields `processed_with_ocr` + `quality`, shows:
 *   - an "OCR" chip when the document was processed via text recognition,
 *   - an "OCR reprocessing" chip while the escalation is running (document is
 *     PROCESSING with a negative first-pass verdict, not yet OCR-processed),
 *   - a "Limited text quality" warning chip when `quality.ok === false`, with
 *     a tooltip showing the concrete `quality.reason`.
 *
 * File-format independent: behaves identically for PDF and scanned DOCX,
 * since the backend populates the same fields for both. Pure presentation
 * component — no data fetching, reused in card and list views.
 */
import React from 'react';
import { Chip, Stack, Tooltip } from '@mui/material';
import { DocumentScanner, WarningAmber, ErrorOutline } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { Document, DocumentStatus } from '../../types/document';

// Mapping of the backend `quality.reason` values to i18n tooltip keys. Dynamic
// keys are deliberately not checked by the i18n parity test — hence an
// explicit fallback (`reasonUnknown`) for future backend reasons.
const QUALITY_REASON_KEY: Record<string, string> = {
  scanned_low_text: 'components.documentLibrary.quality.reasonScannedLowText',
  single_chunk_large_file:
    'components.documentLibrary.quality.reasonSingleChunkLargeFile',
  garbage_extraction: 'components.documentLibrary.quality.reasonGarbageExtraction',
  ocr_pages_discarded: 'components.documentLibrary.quality.reasonOcrPagesDiscarded',
};

export interface DocumentOcrQualityBadgesProps {
  document: Document;
  /** MUI Chip size — `small` (default) fits card and table rows. */
  size?: 'small' | 'medium';
}

const DocumentOcrQualityBadges: React.FC<DocumentOcrQualityBadgesProps> = ({
  document,
  size = 'small',
}) => {
  const { t } = useTranslation();

  const quality = document.quality;
  const qualityFailed = quality != null && quality.ok === false;
  const escalation = document.escalation;

  // OCR post-processing failed (TF-365): the reprocess job set the document to
  // ERROR. Dedicated notice so the otherwise unexplainable PROCESSED→ERROR
  // transition is comprehensible to the user.
  if (escalation === 'failed') {
    return (
      <Tooltip
        title={t(
          'components.documentLibrary.ocr.failedTooltip',
          'Die automatische Texterkennung (OCR) ist fehlgeschlagen. Das Dokument konnte nicht verarbeitet werden.',
        )}
      >
        <Chip
          icon={<ErrorOutline />}
          label={t(
            'components.documentLibrary.ocr.failed',
            'OCR-Nachbearbeitung fehlgeschlagen',
          )}
          color="error"
          size={size}
          variant="outlined"
          data-testid="ocr-failed-badge"
        />
      </Tooltip>
    );
  }

  // OCR reprocessing is running (TF-360/TF-365): preferably detected via the
  // exposed `escalation` marker. `queued` covers both waiting in the Celery
  // queue (document still PROCESSED — window A, otherwise invisible) and the
  // already-running reprocess (PROCESSING). The status heuristic remains as a
  // fallback for legacy rows whose processing_info doesn't yet carry a marker.
  const ocrReprocessing =
    escalation === 'queued' ||
    (document.status === DocumentStatus.PROCESSING &&
      qualityFailed &&
      !document.processed_with_ocr);

  if (ocrReprocessing) {
    // Only show this notice during reprocessing — the contradictory quality
    // warning chip from the first pass would otherwise appear alongside it.
    return (
      <Tooltip
        title={t(
          'components.documentLibrary.ocr.reprocessingTooltip',
          'Das Dokument wird per Texterkennung (OCR) neu verarbeitet.',
        )}
      >
        <Chip
          icon={<DocumentScanner />}
          label={t('components.documentLibrary.ocr.reprocessing', 'OCR-Neuverarbeitung')}
          color="warning"
          size={size}
          variant="outlined"
          data-testid="ocr-reprocessing-badge"
        />
      </Tooltip>
    );
  }

  const badges: React.ReactNode[] = [];

  if (document.processed_with_ocr) {
    badges.push(
      <Tooltip
        key="ocr"
        title={t(
          'components.documentLibrary.ocr.badgeTooltip',
          'Mit Texterkennung (OCR) verarbeitet',
        )}
      >
        <Chip
          icon={<DocumentScanner />}
          label={t('components.documentLibrary.ocr.badge', 'OCR')}
          color="info"
          size={size}
          variant="outlined"
          data-testid="ocr-badge"
        />
      </Tooltip>,
    );
  }

  if (qualityFailed) {
    const reasonKey =
      QUALITY_REASON_KEY[quality!.reason] ??
      'components.documentLibrary.quality.reasonUnknown';
    const discardedRaw = quality!.signals?.ocr_pages_discarded;
    const discardedCount =
      typeof discardedRaw === 'number' ? discardedRaw : Number(discardedRaw) || 0;
    badges.push(
      <Tooltip
        key="quality"
        title={t(reasonKey, {
          count: discardedCount,
          defaultValue: 'Eingeschränkte Textqualität festgestellt.',
        })}
      >
        <Chip
          icon={<WarningAmber />}
          label={t('components.documentLibrary.quality.limited', 'Eingeschränkte Textqualität')}
          color="warning"
          size={size}
          variant="outlined"
          data-testid="quality-warning-badge"
          data-ocr-discarded={
            quality!.reason === 'ocr_pages_discarded' && discardedCount > 0
              ? discardedCount
              : undefined
          }
        />
      </Tooltip>,
    );
  }

  if (badges.length === 0) {
    return null;
  }

  return (
    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
      {badges}
    </Stack>
  );
};

export default DocumentOcrQualityBadges;
