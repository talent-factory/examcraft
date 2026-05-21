/**
 * Notenexport-Panel — TF-335 Spec 9.
 *
 * Drei Formate (CSV / Moodle-CSV / PDF) per Radio. Download-Button
 * deaktiviert solange noch Submissions im Status `pending_review` oder
 * `partially_reviewed` sind — der Backend-Endpoint blockiert mit 409
 * (i18n key `submissions_grade_export_blocked_pending_review`), aber
 * wir spiegeln die Sperre auch im UI, damit der Button nicht
 * scheinbar nichts tut.
 *
 * Ein Hinweis-Banner mit Link zur Review-Queue zeigt sich, wenn der
 * Export aktuell blockiert ist.
 */

import React, { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormLabel,
  Link,
  Paper,
  Radio,
  RadioGroup,
  Typography,
} from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

import {
  ExportFormat,
  GradeExportService,
} from '../../services/gradeExportService';
import { ApiError } from '../../services/submissionsService';

interface NotenexportPanelProps {
  examId: number;
  /**
   * Counts surfaced from the submissions list so we can show the
   * review-progress hint without fetching anything extra. The export
   * is unlocked when ``pendingCount === 0``.
   */
  totalSubmissions: number;
  pendingCount: number;
  /** Click handler: opens the Review tab so the user can clear the queue. */
  onOpenReview?: () => void;
}

const FORMATS: ExportFormat[] = ['csv', 'moodle_csv', 'pdf'];

const NotenexportPanel: React.FC<NotenexportPanelProps> = ({
  examId,
  totalSubmissions,
  pendingCount,
  onOpenReview,
}) => {
  const { t } = useTranslation();
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const blocked = pendingCount > 0 || totalSubmissions === 0;

  const handleDownload = async () => {
    setDownloading(true);
    setError(null);
    try {
      const { blob, filename } = await GradeExportService.download(
        examId,
        format,
      );
      // Trigger browser download via temporary anchor.
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      if (err instanceof ApiError) {
        // Branch on err.kind so the lehrperson sees an actionable
        // message instead of "Export failed (500)". Conflict (409)
        // surfaces the backend's translated detail directly because
        // it carries the specific reason (pending review vs. draft
        // status vs. "etwas anderes").
        switch (err.kind) {
          case 'auth':
            setError(t('auswertungen.export.errorAuth'));
            break;
          case 'permission':
            setError(t('auswertungen.export.errorPermission'));
            break;
          case 'not_found':
            setError(t('auswertungen.export.errorNotFound'));
            break;
          case 'conflict':
            setError(err.message);
            break;
          default:
            setError(t('auswertungen.export.errorServer'));
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('auswertungen.export.unexpectedError'));
      }
    } finally {
      setDownloading(false);
    }
  };

  const reviewHint = useMemo(() => {
    if (totalSubmissions === 0) {
      return t('auswertungen.export.noSubmissionsHint');
    }
    if (pendingCount > 0) {
      return t('auswertungen.export.pendingReviewHint', {
        count: pendingCount,
      });
    }
    return null;
  }, [pendingCount, totalSubmissions, t]);

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        {t('auswertungen.export.title')}
      </Typography>

      {reviewHint && (
        <Alert
          severity="warning"
          sx={{ mb: 3 }}
          data-testid="notenexport-blocked-hint"
        >
          {reviewHint}{' '}
          {pendingCount > 0 && onOpenReview && (
            <Link
              component="button"
              onClick={onOpenReview}
              data-testid="notenexport-open-review"
            >
              {t('auswertungen.export.openReviewQueue')}
            </Link>
          )}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="notenexport-error">
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3, mb: 3 }}>
        <FormControl>
          <FormLabel>{t('auswertungen.export.formatLabel')}</FormLabel>
          <RadioGroup
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
            data-testid="notenexport-format-radio"
          >
            {FORMATS.map((f) => (
              <FormControlLabel
                key={f}
                value={f}
                control={<Radio />}
                label={t(`auswertungen.export.format.${f}`)}
                data-testid={`notenexport-format-${f}`}
              />
            ))}
          </RadioGroup>
        </FormControl>
      </Paper>

      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
        <Button
          variant="contained"
          startIcon={
            downloading ? (
              <CircularProgress size={16} color="inherit" />
            ) : (
              <DownloadIcon />
            )
          }
          disabled={blocked || downloading}
          onClick={handleDownload}
          data-testid="notenexport-download-button"
        >
          {t('auswertungen.export.downloadButton')}
        </Button>
        <Typography variant="body2" color="text.secondary">
          {t('auswertungen.export.summary', {
            total: totalSubmissions,
            pending: pendingCount,
          })}
        </Typography>
      </Box>
    </Box>
  );
};

export default NotenexportPanel;
