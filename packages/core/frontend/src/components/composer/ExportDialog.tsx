import React, { useState } from 'react';
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

type ExportFormat = 'md' | 'json' | 'moodle';

const FORMAT_LABELS: Record<ExportFormat, string> = {
  md: 'Markdown (.md)',
  json: 'JSON (.json)',
  moodle: 'Moodle XML (.xml)',
};

const ExportDialog: React.FC<ExportDialogProps> = ({
  open,
  onClose,
  examId,
  examTitle,
  hasQuestions,
}) => {
  const [format, setFormat] = useState<ExportFormat>('md');
  const [includeSolutions, setIncludeSolutions] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(null);
    try {
      await ComposerService.downloadExport(
        examId,
        format,
        format === 'md' ? includeSolutions : false
      );
      onClose();
    } catch (err) {
      console.error('Export failed:', err);
      // Try to extract detail from blob response for better error messages
      let message = 'Export fehlgeschlagen. Bitte versuche es erneut.';
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
      <DialogTitle>Prüfung exportieren</DialogTitle>
      <DialogContent>
        <p className="text-sm text-gray-600 mb-4">
          <strong>{examTitle}</strong>
        </p>

        <FormControl component="fieldset" fullWidth>
          <FormLabel component="legend" className="text-sm font-medium text-gray-700 mb-2">
            Format
          </FormLabel>
          <RadioGroup
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
          >
            {(Object.keys(FORMAT_LABELS) as ExportFormat[]).map((f) => (
              <FormControlLabel
                key={f}
                value={f}
                control={<Radio size="small" />}
                label={FORMAT_LABELS[f]}
              />
            ))}
          </RadioGroup>
        </FormControl>

        {format === 'md' && (
          <div className="mt-3">
            <FormControlLabel
              control={
                <Checkbox
                  size="small"
                  checked={includeSolutions}
                  onChange={(e) => setIncludeSolutions(e.target.checked)}
                />
              }
              label="Loesungen einschliessen"
            />
          </div>
        )}

        {!hasQuestions && (
          <p className="text-amber-600 text-sm mt-3">
            Die Prüfung hat noch keine Fragen. Füge zuerst Fragen hinzu.
          </p>
        )}

        {error && (
          <p className="text-red-500 text-sm mt-2">{error}</p>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isDownloading}>
          Abbrechen
        </Button>
        <Button
          onClick={handleDownload}
          variant="contained"
          disabled={!hasQuestions || isDownloading}
        >
          {isDownloading ? 'Exportiere...' : 'Herunterladen'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ExportDialog;
