import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  RadioGroup,
  FormControlLabel,
  Radio,
  Box,
  CircularProgress,
  Alert,
  Tooltip,
} from '@mui/material';
import { LockOutlined, Business } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { DocumentVisibility } from '../types/document';

interface DocumentVisibilityDialogProps {
  open: boolean;
  /** Current visibility of the document being edited. */
  current: DocumentVisibility;
  /** Institution name, interpolated into the "institution" option label. */
  institutionName?: string;
  /** Whether the user belongs to an institution; gates the institution option. */
  hasInstitution: boolean;
  saving?: boolean;
  error?: string | null;
  onClose: () => void;
  onSave: (visibility: DocumentVisibility) => void;
}

/**
 * Quick-edit dialog for a document's visibility (TF-354). Owner-only on the
 * backend; the caller is responsible for only opening it for owners. Extracted
 * as a standalone component because Ticket B reuses it from the bulk-actions
 * bar.
 */
export const DocumentVisibilityDialog: React.FC<DocumentVisibilityDialogProps> = ({
  open,
  current,
  institutionName = '',
  hasInstitution,
  saving = false,
  error = null,
  onClose,
  onSave,
}) => {
  const { t } = useTranslation();
  const [value, setValue] = useState<DocumentVisibility>(current);

  // Re-seed the selection whenever the dialog (re)opens on a new document.
  useEffect(() => {
    if (open) {
      setValue(current);
    }
  }, [open, current]);

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{t('components.documentVisibility.title')}</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <RadioGroup
          value={value}
          onChange={(e) => setValue(e.target.value as DocumentVisibility)}
        >
          <FormControlLabel
            value={DocumentVisibility.PRIVATE}
            control={<Radio />}
            disabled={saving}
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LockOutlined fontSize="small" />
                {t('components.documentVisibility.private')}
              </Box>
            }
          />
          <Tooltip
            title={hasInstitution ? '' : t('components.documentVisibility.noInstitution')}
            placement="right"
          >
            {/* span keeps the tooltip working while the control is disabled */}
            <span>
              <FormControlLabel
                value={DocumentVisibility.INSTITUTION}
                control={<Radio />}
                disabled={!hasInstitution || saving}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Business fontSize="small" />
                    {t('components.documentVisibility.institution', {
                      institution: institutionName,
                    })}
                  </Box>
                }
              />
            </span>
          </Tooltip>
        </RadioGroup>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          {t('components.documentVisibility.cancel')}
        </Button>
        <Button
          variant="contained"
          onClick={() => onSave(value)}
          disabled={saving || value === current}
        >
          {saving ? (
            <CircularProgress size={20} />
          ) : (
            t('components.documentVisibility.save')
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DocumentVisibilityDialog;
