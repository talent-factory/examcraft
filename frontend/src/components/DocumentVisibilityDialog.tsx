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
  Select,
  MenuItem,
  FormControl,
} from '@mui/material';
import { LockOutlined, Business, Groups } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { DocumentVisibility } from '../types/document';
import { OrgUnitOut } from '../types/orgUnit';

interface DocumentVisibilityDialogProps {
  open: boolean;
  /** Current visibility of the document being edited. Null means no pre-selection (bulk mode). */
  current: DocumentVisibility | null;
  /** Current Org-Unit scope, when `current` is 'team' (TF-620). */
  currentOrgUnitId?: number | null;
  /** Institution name, interpolated into the "institution" option label. */
  institutionName?: string;
  /** Whether the user belongs to an institution; gates the institution option. */
  hasInstitution: boolean;
  /** Caller's own Org-Unit memberships (TF-620) — gates/populates the team option. */
  orgUnits?: OrgUnitOut[];
  /** True when fetching `orgUnits` failed — distinguishes "no memberships" from "couldn't check" (TF-620). */
  orgUnitsLoadError?: boolean;
  saving?: boolean;
  error?: string | null;
  onClose: () => void;
  onSave: (visibility: DocumentVisibility, orgUnitId?: number | null) => void;
}

/**
 * Quick-edit dialog for a document's visibility (TF-354, TF-620 'team' tier).
 * Owner-only on the backend; the caller is responsible for only opening it
 * for owners. Extracted as a standalone component because Ticket B reuses it
 * from the bulk-actions bar.
 */
export const DocumentVisibilityDialog: React.FC<DocumentVisibilityDialogProps> = ({
  open,
  current,
  currentOrgUnitId = null,
  institutionName = '',
  hasInstitution,
  orgUnits = [],
  orgUnitsLoadError = false,
  saving = false,
  error = null,
  onClose,
  onSave,
}) => {
  const { t } = useTranslation();
  const [value, setValue] = useState<DocumentVisibility | null>(current);
  const [orgUnitId, setOrgUnitId] = useState<number | null>(currentOrgUnitId);
  const hasOrgUnits = orgUnits.length > 0;

  // Re-seed the selection whenever the dialog (re)opens on a new document.
  useEffect(() => {
    if (open) {
      setValue(current);
      setOrgUnitId(currentOrgUnitId);
    }
  }, [open, current, currentOrgUnitId]);

  const isUnchanged =
    value === current &&
    (value !== DocumentVisibility.TEAM || orgUnitId === currentOrgUnitId);
  const isIncompleteTeamSelection =
    value === DocumentVisibility.TEAM && orgUnitId === null;

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
          value={value ?? ''}
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
            title={
              hasOrgUnits
                ? ''
                : orgUnitsLoadError
                  ? t('components.documentVisibility.orgUnitsLoadError')
                  : t('components.documentVisibility.noOrgUnit')
            }
            placement="right"
          >
            {/* span keeps the tooltip working while the control is disabled */}
            <span>
              <FormControlLabel
                value={DocumentVisibility.TEAM}
                control={<Radio />}
                disabled={!hasOrgUnits || saving}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Groups fontSize="small" />
                    {t('components.documentVisibility.team')}
                  </Box>
                }
              />
            </span>
          </Tooltip>
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
        {value === DocumentVisibility.TEAM && (
          <FormControl size="small" sx={{ mt: 1, ml: 4, minWidth: 220 }}>
            {/* TF-626: siehe DocumentUpload.tsx — Generic explizit, sonst
                gilt der '' -Vergleich in renderValue als unmoeglich. */}
            <Select<number | ''>
              displayEmpty
              value={orgUnitId ?? ''}
              onChange={(e) => setOrgUnitId(e.target.value === '' ? null : Number(e.target.value))}
              disabled={saving}
              renderValue={(v) =>
                v === ''
                  ? t('components.documentVisibility.orgUnitPickerPlaceholder')
                  : orgUnits.find(ou => ou.id === v)?.name ?? ''
              }
            >
              {orgUnits.map(ou => (
                <MenuItem key={ou.id} value={ou.id}>
                  {ou.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          {t('components.documentVisibility.cancel')}
        </Button>
        <Button
          variant="contained"
          onClick={() =>
            value &&
            onSave(value, value === DocumentVisibility.TEAM ? orgUnitId : undefined)
          }
          disabled={saving || value === null || isUnchanged || isIncompleteTeamSelection}
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
