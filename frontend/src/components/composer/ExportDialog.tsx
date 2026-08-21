import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControlLabel,
  Checkbox,
  FormControl,
  FormLabel,
  RadioGroup,
  Radio,
} from '@mui/material';
import { ComposerService } from '../../services/ComposerService';

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
  examId: number;
  examTitle: string;
  hasQuestions: boolean;
}

type ExportFormat = 'md' | 'json' | 'moodle' | 'pdf';

// Formats that render the exam for humans and can therefore carry a
// sample-solution variant. JSON and Moodle XML always ship the solution
// data as part of their payload, so the toggle is meaningless there.
const SOLUTION_CAPABLE_FORMATS: ExportFormat[] = ['md', 'pdf'];

const ExportDialog: React.FC<ExportDialogProps> = ({
  open,
  onClose,
  examId,
  examTitle,
  hasQuestions,
}) => {
  const { t, i18n } = useTranslation();
  const [format, setFormat] = useState<ExportFormat>('md');
  const [includeSolutions, setIncludeSolutions] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const FORMAT_LABELS: Record<ExportFormat, string> = {
    md: t('composer.exportDialog.formatMd'),
    pdf: t('composer.exportDialog.formatPdf'),
    json: t('composer.exportDialog.formatJson'),
    moodle: t('composer.exportDialog.formatMoodle'),
  };

  const supportsSolutions = SOLUTION_CAPABLE_FORMATS.includes(format);

  // Sorted by what the user actually reads, not by key order — an
  // alphabetical list is quicker to scan than an editorial one. Sorting on
  // the translated label (rather than a fixed order) keeps it alphabetical
  // in every locale, using that locale's collation rules.
  const orderedFormats = (Object.keys(FORMAT_LABELS) as ExportFormat[]).sort(
    (a, b) => FORMAT_LABELS[a].localeCompare(FORMAT_LABELS[b], i18n.language)
  );

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(null);
    try {
      await ComposerService.downloadExport(
        examId,
        format,
        supportsSolutions ? includeSolutions : false
      );
      onClose();
    } catch (err) {
      console.error('Export failed:', err);
      // Try to extract detail from blob response for better error messages
      let message = t('composer.exportDialog.errorExport');
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: Blob | { detail?: string }; headers?: Record<string, string> } };
        const responseData = axiosError.response?.data;
        if (responseData instanceof Blob && responseData.type === 'application/json') {
          try {
            const text = await responseData.text();
            const parsed = JSON.parse(text) as { detail?: string };
            if (parsed.detail) {
              message = parsed.detail;
            }
          } catch {
            // ignore parse errors, keep fallback message
          }
        } else if (responseData && typeof responseData === 'object' && 'detail' in responseData && responseData.detail) {
          message = responseData.detail as string;
        }
      }
      setError(message);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleClose = () => {
    if (!isDownloading) {
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>{t('composer.exportDialog.title')}</DialogTitle>
      <DialogContent>
        <p className="text-sm text-gray-600 mb-4">
          <strong>{examTitle}</strong>
        </p>

        <FormControl component="fieldset" fullWidth>
          <FormLabel component="legend" className="text-sm font-medium text-gray-700 mb-2">
            {t('composer.exportDialog.formatLabel')}
          </FormLabel>
          <RadioGroup
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
          >
            {orderedFormats.map((f) => (
              <FormControlLabel
                key={f}
                value={f}
                control={<Radio size="small" />}
                label={FORMAT_LABELS[f]}
              />
            ))}
          </RadioGroup>
        </FormControl>

        {supportsSolutions && (
          <div className="mt-3">
            <FormControlLabel
              control={
                <Checkbox
                  size="small"
                  checked={includeSolutions}
                  onChange={(e) => setIncludeSolutions(e.target.checked)}
                />
              }
              label={t('composer.exportDialog.includeSolutions')}
            />
          </div>
        )}

        {!hasQuestions && (
          <p className="text-amber-600 text-sm mt-3">
            {t('composer.exportDialog.noQuestionsWarning')}
          </p>
        )}

        {error && (
          <p className="text-red-500 text-sm mt-2">{error}</p>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isDownloading}>
          {t('composer.exportDialog.cancel')}
        </Button>
        <Button
          onClick={handleDownload}
          variant="contained"
          disabled={!hasQuestions || isDownloading}
        >
          {isDownloading ? t('composer.exportDialog.exporting') : t('composer.exportDialog.download')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ExportDialog;
