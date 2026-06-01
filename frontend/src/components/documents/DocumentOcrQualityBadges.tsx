/**
 * DocumentOcrQualityBadges — OCR-/Qualitäts-Status-Badges (TF-361).
 *
 * Folge-Ticket zur Backend-OCR-Eskalation (TF-360). Zeigt anhand der vom
 * Backend exponierten Felder `processed_with_ocr` + `quality`:
 *   - „OCR"-Chip, wenn das Dokument per Texterkennung verarbeitet wurde,
 *   - „OCR-Neuverarbeitung"-Chip, während die Eskalation läuft (Dokument auf
 *     PROCESSING mit negativem Erstlauf-Verdict, noch nicht OCR-verarbeitet),
 *   - Warn-Chip „Eingeschränkte Textqualität" bei `quality.ok === false`, mit
 *     Tooltip auf den konkreten `quality.reason`.
 *
 * Dateiformat-unabhängig: greift identisch für PDF und gescanntes DOCX, da das
 * Backend für beide dieselben Felder befüllt. Reine Präsentationskomponente —
 * keine Datenbeschaffung, wird in Karten- und Listen-Ansicht wiederverwendet.
 */
import React from 'react';
import { Chip, Stack, Tooltip } from '@mui/material';
import { DocumentScanner, WarningAmber, ErrorOutline } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { Document, DocumentStatus } from '../../types/document';

// Mapping der Backend-`quality.reason`-Werte auf i18n-Tooltip-Keys. Dynamische
// Keys werden vom i18n-Parity-Test bewusst nicht geprüft — daher ein
// expliziter Fallback (`reasonUnknown`) für künftige Backend-Reasons.
const QUALITY_REASON_KEY: Record<string, string> = {
  scanned_low_text: 'components.documentLibrary.quality.reasonScannedLowText',
  single_chunk_large_file:
    'components.documentLibrary.quality.reasonSingleChunkLargeFile',
  garbage_extraction: 'components.documentLibrary.quality.reasonGarbageExtraction',
  ocr_pages_discarded: 'components.documentLibrary.quality.reasonOcrPagesDiscarded',
};

export interface DocumentOcrQualityBadgesProps {
  document: Document;
  /** MUI Chip size — `small` (default) passt in Karten- und Tabellenzeilen. */
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

  // OCR-Nachbearbeitung fehlgeschlagen (TF-365): der Reprocess-Job hat das
  // Dokument auf ERROR gesetzt. Eigener Hinweis, damit der für den Nutzer sonst
  // unerklärliche PROCESSED→ERROR-Übergang nachvollziehbar wird.
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

  // OCR-Neuverarbeitung läuft (TF-360/TF-365): bevorzugt am exponierten
  // `escalation`-Marker erkannt. `queued` deckt sowohl das Warten in der Celery-
  // Queue (Dokument noch PROCESSED — Fenster A, sonst unsichtbar) als auch den
  // bereits laufenden Reprocess (PROCESSING) ab. Die Status-Heuristik bleibt als
  // Fallback für Altrows, deren processing_info noch keinen Marker trägt.
  const ocrReprocessing =
    escalation === 'queued' ||
    (document.status === DocumentStatus.PROCESSING &&
      qualityFailed &&
      !document.processed_with_ocr);

  if (ocrReprocessing) {
    // Während der Neuverarbeitung nur diesen Hinweis zeigen — der widersprüchliche
    // Qualitäts-Warnchip aus dem Erstlauf würde sonst doppelt erscheinen.
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
